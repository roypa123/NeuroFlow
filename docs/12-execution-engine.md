# 12 — Execution Engine

The engine turns a stored graph into results. It lives in `app/engine/`, runs only in worker
processes, and is the single most correctness-critical component in the system.

## 12.1 The data model: items

Everything that flows between nodes is a **list of items**. (ADR-008)

```python
@dataclass(slots=True)
class Item:
    json: dict[str, Any]
    binary: dict[str, BinaryRef] | None = None
    paired_item: PairedItem | None = None   # provenance: which input item produced this

NodeOutput = dict[str, list[list[Item]]]   # { "main": [ [items for output 0], [output 1] ] }
```

This is n8n's model, adopted deliberately rather than by imitation. Its consequences are what make
the whole product work:

- **Fan-out is free.** A node returning 24 items causes the next node to run 24 times. No explicit
  loop construct is needed for the common case, which is most of the value.
- **Uniform UI.** Every data panel renders the same shape, so one `DataView` component serves the
  entire product.
- **Provenance is expressible.** `paired_item` links an output item to the input item that caused
  it, which is what makes "why did this row produce that result?" answerable in the UI.

The alternative — a single JSON blob per node — is simpler to implement and immediately forces
users to hand-write loops for the most common operation there is. Not worth it.

**Binary data is never inline.** `BinaryRef` holds `{objectKey, mimeType, fileName, sizeBytes}`;
bytes live in the object store. This keeps `execution_data` rows small and makes a 40 MB PDF a
reference rather than a base64 string in Postgres.

## 12.2 Execution lifecycle

```python
async def run_execution(execution_id: UUID) -> None:
    execution = await service.load(execution_id)
    graph     = await service.load_graph(execution.workflow_version_id)   # pinned version
    dag       = DAG.from_graph(graph)                    # validate: cycles, orphans, unknown types
    ctx       = ExecutionContext(execution, graph, settings)

    await service.mark_running(execution_id)
    try:
        await execute_dag(dag, ctx)
        await service.finish(execution_id, "success")
    except ExecutionSuspended as s:
        await service.suspend(execution_id, s.resume_token, s.resume_after)
    except NodeExecutionError as e:
        await service.finish(execution_id, "error", error=e.to_dict())
        await maybe_trigger_error_workflow(ctx, e)
    finally:
        await ctx.close()          # release http clients, subprocesses, temp files
```

**The version is pinned at enqueue time**, so editing a workflow while it runs cannot change what
that run does. This one decision eliminates an entire category of "it worked yesterday"
irreproducibility.

## 12.3 Scheduling

Not a naive topological sort — branch nodes mean not every node runs.

```python
async def execute_dag(dag: DAG, ctx: ExecutionContext) -> None:
    ready: deque[NodeRun] = deque(dag.trigger_nodes())
    completed: set[str] = set()

    while ready:
        batch = _take_parallelizable(ready, ctx.max_parallel)   # independent nodes only
        results = await asyncio.gather(
            *(run_node(n, ctx) for n in batch), return_exceptions=True
        )
        for node, result in zip(batch, results):
            _handle(node, result, ctx, completed)
            for successor in dag.successors_via(node, result.active_outputs):
                if dag.inputs_satisfied(successor, completed):
                    ready.append(NodeRun(successor, _gather_inputs(successor, ctx)))
```

Key behaviours:

- **A node runs when all its *reachable* inputs are satisfied.** "Reachable" matters: if an IF node
  took the true branch, a downstream Merge must not wait forever on the false branch. The DAG
  computes reachability after each branch decision and marks unreachable nodes `skipped`.
- **Independent branches run in parallel**, bounded by `max_parallel` (default 5) to keep one
  workflow from monopolising a worker.
- **Fan-out is per-item within a node**, not by scheduling N node instances — the node's
  `execute()` receives all items and the runtime decides whether to loop.

### Loops

Two forms, and they are genuinely different:

1. **Implicit** — a node returns N items; downstream nodes process all N. No loop node exists.
   This covers the majority of real workflows.
2. **Explicit** — a `SplitInBatches` / `Loop` node with a back-edge, for batching, pagination, and
   agent iteration. The DAG permits exactly one back-edge per loop node, enforces a
   `maxIterations` ceiling (default 1000), and increments `run_index` on every node inside the
   loop so history is preserved per iteration rather than overwritten.

## 12.4 Node execution

```python
async def run_node(run: NodeRun, ctx: ExecutionContext) -> NodeResult:
    node_type = registry.get(run.node.type, run.node.type_version)
    node_exec = await ctx.record_start(run)

    try:
        params = await ctx.resolve_parameters(run.node, run.input_items)   # expressions
        creds  = await ctx.resolve_credentials(run.node)                   # decrypt (worker only)

        async with ctx.node_timeout(run.node):                             # per-node deadline
            output = await node_type.execute(
                NodeExecutionContext(params, run.input_items, creds, ctx)
            )

        await ctx.record_success(node_exec, output)
        return NodeResult.ok(output)

    except Exception as exc:
        return await _handle_node_error(run, node_exec, exc, ctx)
```

### Error handling per node

Configured on the node itself (`onError` in the graph document):

| `onError` | Behaviour |
|---|---|
| `stop` (default) | Fail the whole execution |
| `continue` | Emit the error as an item on the main output; downstream nodes carry on |
| `continueErrorOutput` | Route to the node's dedicated **error output**, enabling a visible failure branch on the canvas |

### Retries

Per node: `maxTries` (default 3), `waitBetweenTries` (default 1000 ms), exponential backoff with
jitter via `tenacity`. Retries respect `Retry-After` on 429 and 503.

**Only idempotent-declared nodes are retried automatically.** A node descriptor carries an
`idempotent: bool`; a POST that creates a charge is not retried without the author opting in.
Silently retrying non-idempotent operations is how automation platforms create duplicate invoices.

## 12.5 Suspension and resume

A Wait node, an approval node, or a long-delay timer **suspends** the execution and releases the
worker:

```python
raise ExecutionSuspended(
    resume_token=secrets.token_urlsafe(32),
    resume_after=datetime.now(UTC) + timedelta(hours=24),
    checkpoint=ctx.snapshot(),
)
```

The execution goes to `waiting`. Two ways it comes back:

1. **Time-based** — the scheduler picks up rows whose `resume_after` has passed.
2. **Event-based** — `POST /executions/{id}/resume` with the token (an approval link, a callback).

On resume, a fresh worker rehydrates completed node outputs from `node_executions` and continues
from the suspension point. Because state lives in Postgres rather than worker memory, a wait of
30 days costs nothing but a row — which is what makes human-in-the-loop workflows practical
instead of theoretical.

## 12.6 Expressions

Parameters can contain `{{ … }}` expressions, evaluated against the current item.

```
={{ $json.customer.email }}
={{ $node["Fetch orders"].json.total > 100 ? "vip" : "standard" }}
={{ $items().length }} orders on {{ $now.format("YYYY-MM-DD") }}
={{ $vars.API_BASE }}/v2/customers
```

The leading `=` marks a parameter as an expression rather than a literal — a string containing
`{{` should not be silently reinterpreted.

### Scope

| Symbol | Meaning |
|---|---|
| `$json` | Current item's JSON |
| `$binary` | Current item's binary refs |
| `$item(i)` | Another item in the current input |
| `$items()` | All input items |
| `$node["Name"]` | Output of a named upstream node |
| `$workflow` | `{ id, name, active }` |
| `$execution` | `{ id, mode, resumeUrl }` |
| `$now`, `$today` | Timezone-aware datetimes (workflow timezone) |
| `$vars` | Project/org variables |
| `$env` | Allow-listed environment variables only |
| `$runIndex` | Current loop iteration |

### Sandboxing (ADR-010)

**Expressions are never `eval`-ed.** The evaluator:

1. Tokenises and parses to an AST with a restricted grammar.
2. Rejects attribute access to dunder names, `import`, comprehension-based resource exhaustion,
   and any identifier not in the allow-list.
3. Executes with a whitelisted builtin set (string/number/date/array helpers, `JSON`, `Math`),
   no filesystem, no network, no `open`.
4. Enforces a 100 ms CPU budget and a 1 MB result cap per expression.

An expression failure is a node error with the offending expression and the resolved scope
attached — "cannot read property 'email' of undefined" without saying *which* expression is a
support ticket.

⚠️ **`$env` is allow-listed, not open.** Exposing the worker's whole environment to expressions
would hand every workflow author the database password.

## 12.7 The Code node

Arbitrary user JavaScript. The most dangerous feature in the product, so it gets the strongest
isolation:

- Runs in a **separate subprocess** (Node.js with a restricted context), never in the worker's
  event loop.
- Hard limits: 30 s wall clock, 128 MB memory, no network by default (opt-in per instance via
  configuration), no filesystem, no `require` beyond an allow-list.
- The subprocess runs as an unprivileged user; in production deployments it should additionally be
  confined with seccomp or gVisor.
- Two modes: **run once for all items** (receives `items`) and **run once per item** (receives
  `item`) — a naming choice that saves a great deal of confusion later.

Full threat model in [15](./15-security-and-credentials.md) §15.8.

## 12.8 Concurrency and fairness

| Level | Control |
|---|---|
| Per worker | `max_jobs` (default 10 concurrent executions) |
| Per execution | `max_parallel` nodes (default 5) |
| Per workflow | `maxConcurrency` setting; a Redis lock prevents overlapping runs of the same workflow |
| Per org | Queue quota; excess jobs queue rather than starve other tenants |

`maxConcurrency: 1` is the correct default for any workflow with a cursor or a shared external
resource, and the UI should suggest it when a workflow writes to a database.

**Queue fairness:** a single tenant enqueuing 10,000 executions must not starve everyone else.
arq gives FIFO per queue, so we shard by org into a small number of queues and workers round-robin
across them. Not perfect fairness, but it prevents the pathological case at low complexity.

## 12.9 Timeouts

Every layer has one, because unbounded waits are how workers leak:

| Scope | Default | Configurable at |
|---|---|---|
| Whole execution | 3600 s | workflow settings |
| Single node | 300 s | node settings |
| HTTP request | 30 s | node parameter |
| Expression | 100 ms | fixed |
| Code node | 30 s | fixed |
| LLM call | 120 s | node parameter |

Timeout errors are ordinary node errors, so they participate in retries and error branches.

## 12.10 Observability hooks

The engine emits events at every meaningful boundary, published to Redis
`exec:{execution_id}` and relayed to browsers via SSE:

```
execution.started · node.started · node.finished · node.log
node.retrying     · execution.suspended · execution.finished
```

Every event carries `executionId`, `nodeId` (where applicable), a monotonic sequence, and a
timestamp. The sequence number is what lets a reconnecting SSE client detect a gap and refetch
instead of silently rendering an incomplete run.

Node authors emit progress via `ctx.log(level, message)`, which is captured, persisted with the
node execution, and streamed live.

## 12.11 Failure recovery

| Scenario | Recovery |
|---|---|
| Worker killed mid-node | arq re-queues after visibility timeout; completed node outputs are reused; the interrupted node re-runs only if declared idempotent, otherwise the execution fails cleanly |
| Postgres unavailable mid-execution | Job fails and re-queues; work is lost but not corrupted, since every write is a committed transaction |
| Redis flush | Queued jobs vanish; a sweeper re-enqueues `queued` executions older than 5 minutes |
| Execution stuck `running` | A watchdog marks executions running longer than their timeout + grace as `error` with `code: "execution.timeout"` |
| Object store unavailable | Payload writes fail the node; small payloads still work since they are inline |

**Idempotency is the crux.** The engine cannot know whether a partially-executed node had external
side effects, so it never guesses: it replays only what the node's author declared safe to replay.

## 12.12 Performance targets

| Metric | Target |
|---|---|
| Engine overhead per node (excl. node I/O) | < 15 ms |
| Execution pickup latency (p95) | < 1 s |
| Expression evaluation | < 1 ms typical |
| 100-node linear workflow, trivial nodes | < 3 s end to end |
| Concurrent executions per worker | 10 (I/O-bound) |
| Memory per execution | < 100 MB with payload offloading |

Optimisations that matter, in order of payoff: cache the compiled DAG per workflow version; batch
`node_execution` writes where ordering permits; reuse one `httpx.AsyncClient` per execution
context; and compile expressions once per parameter rather than per item — the last one is a 10×
difference on a 1000-item fan-out.
