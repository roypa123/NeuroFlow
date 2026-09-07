# 16 — Observability

Two audiences with different needs, and conflating them is the usual mistake:

- **The user** asks "why did *my workflow* fail?" — answered by execution records and the data
  panel, which are product features.
- **The operator** asks "why is *the system* slow?" — answered by logs, metrics, and traces.

This document covers both, because in this product the boundary between them is thin: a user's
failed execution is often an operator's incident.

## 16.1 Structured logging

`structlog`, JSON to stdout. The container runtime handles shipping — no log files, no rotation
logic in the application.

```json
{
  "timestamp": "2026-09-07T14:03:22.481Z",
  "level": "error",
  "event": "node.execution_failed",
  "request_id": "01931f2a-8c4e-7a11-b3d2-2f1c9e0a4d55",
  "execution_id": "01931f2b-…",
  "workflow_id": "01931f0a-…",
  "node_id": "n_a1b2",
  "node_type": "neuroflow.http",
  "org_id": "01931e00-…",
  "user_id": "01931e01-…",
  "duration_ms": 30021,
  "error_code": "http.timeout",
  "message": "Request to api.stripe.com timed out after 30s"
}
```

**Context binding, not manual passing.** Middleware binds `request_id`, `user_id`, and `org_id` to
a contextvar at the top of the request; the worker binds `execution_id` and `node_id`. Every
subsequent log line in that context carries them automatically. Threading a request id through
forty function signatures is how teams give up on structured logging.

**Rules.**
- `event` is a stable snake_case identifier. Dashboards and alerts key on it, so it never changes.
- No f-strings for variable data — pass fields, so they stay queryable: `log.info("node.finished",
  items=24)`, not `log.info(f"finished with 24 items")`.
- Levels: `debug` (local only), `info` (state changes), `warning` (recovered degradation),
  `error` (failed operation), `critical` (the service cannot function).
- **Every log passes the `SecretRegistry` redaction filter** ([15](./15-security-and-credentials.md) §15.6).
- A user's workflow failing is `info`/`warning` at the system level — it is not a system error, and
  treating it as one makes error dashboards useless within a week.

## 16.2 Request logging

One line per request, emitted by middleware at response time:

```
event=http.request method=PATCH path=/api/v1/workflows/{id} status=200
duration_ms=47 request_id=… user_id=… org_id=… bytes_out=8214
```

Path templates, not concrete paths — `/workflows/{id}`, never `/workflows/019…`. Otherwise
cardinality explodes and no aggregation is possible. Health checks and `/metrics` are excluded.

## 16.3 Metrics

`prometheus-client`, exposed at `/metrics` on the internal network only.

### RED metrics for the API

```
http_requests_total{method,path,status}                  counter
http_request_duration_seconds{method,path}               histogram
http_requests_in_flight                                  gauge
```

### Execution metrics — the ones that actually matter here

```
executions_total{status,mode,org}                        counter
execution_duration_seconds{workflow_kind}                histogram
execution_queue_depth                                    gauge
execution_queue_wait_seconds                             histogram
executions_active                                        gauge
node_executions_total{node_type,status}                  counter
node_execution_duration_seconds{node_type}               histogram
```

`execution_queue_wait_seconds` is the single most important operational metric in the system. It
is the leading indicator of under-provisioned workers, and it degrades long before users report
anything.

### Agent metrics

```
agent_runs_total{agent,status,stop_reason}               counter
agent_tokens_total{model,type}                           counter
agent_cost_micros_total{model,org}                       counter
agent_iterations                                         histogram
llm_request_duration_seconds{provider,model}             histogram
llm_errors_total{provider,error_type}                    counter
```

Cost as a counter means spend rate is a `rate()` query and budget alerts are a Prometheus rule
rather than a bespoke feature.

### Infrastructure

```
db_pool_size / db_pool_checked_out                       gauge
db_query_duration_seconds{operation}                     histogram
redis_operation_duration_seconds{operation}              histogram
worker_jobs_active{worker}                               gauge
```

**Cardinality discipline.** Never label with `workflow_id`, `execution_id`, or `user_id` — those
are unbounded and will kill Prometheus. `org` is acceptable only for small deployments; for
multi-tenant SaaS, aggregate org-level spend in Postgres and query it there.

## 16.4 Tracing

OpenTelemetry, OTLP export, sampled. `TODO(phase-4)` — valuable but not v1-blocking.

Span structure:

```
POST /api/v1/workflows/{id}/execute        (api)
└── execution.enqueue
    └── execution.run                      (worker — linked span, new trace root)
        ├── node.execute [Webhook]
        ├── node.execute [HTTP Request]
        │   └── http.client GET api.stripe.com
        ├── node.execute [AI Agent]
        │   ├── llm.chat anthropic/claude-opus-5
        │   ├── tool.execute search_docs
        │   │   └── execution.run          (sub-workflow — linked)
        │   └── llm.chat anthropic/claude-opus-5
        └── node.execute [Slack]
```

Execution spans are **linked**, not nested, under the API request: the API span ends at enqueue,
while execution may start seconds later and run for minutes. A parent span held open across that
gap distorts every latency percentile.

Sampling: 100% of errors, 100% of executions slower than 30s, 1% baseline.

## 16.5 Execution observability (the product feature)

What the user sees, and the point where observability becomes UX:

1. **Executions list** — status, workflow, trigger mode, duration, timestamp; filterable by status,
   workflow, date range; keyset-paginated.
2. **Execution detail** — the canvas in read-only mode with per-node status, plus a timeline of
   node runs with durations.
3. **Per-node data** — exact input and output items for every node, in the same `DataView` used
   during editing.
4. **Error detail** — failing node, message, stack, HTTP response body where relevant, and the
   resolved parameters (secrets redacted) that produced the failure.
5. **Live streaming** — SSE-driven status while running.
6. **Retry from failure** — re-run from the failed node, reusing prior outputs.

**Resolved parameters are the underrated one.** Most workflow failures are expression mistakes;
seeing that `url` resolved to `https://api.acme.com/customers/undefined` diagnoses it instantly,
where seeing the expression source does not.

## 16.6 Alerting

Alert on symptoms users feel, not on causes. Every alert must be actionable — an alert nobody acts
on trains everyone to ignore the channel.

| Alert | Condition | Severity |
|---|---|---|
| API error rate | 5xx > 1% over 5 min | page |
| API latency | p95 > 1s over 10 min | page |
| Queue backing up | `queue_wait_seconds` p95 > 60s over 10 min | page |
| Workers down | `executions_active == 0` while `queue_depth > 0` for 5 min | page |
| DB pool exhausted | `checked_out / size > 0.9` for 5 min | page |
| Execution failure rate | > 20% over 15 min (excl. user errors) | ticket |
| LLM provider errors | `llm_errors_total` rate > 10/min | ticket |
| Cost spike | org spend > 3× 7-day average | ticket |
| Cert expiry | < 14 days | ticket |
| Disk | > 80% | ticket |

Note the exclusion on execution failure rate: a customer writing a broken workflow must not page
an engineer. Separating "the platform failed" from "the user's workflow failed" is essential, and
the error taxonomy in [08](./08-backend-architecture.md) §8.5 is what makes it possible.

## 16.7 Health checks

```
GET /health        → 200 {"status":"ok"}          liveness; NO dependency checks
GET /health/ready  → 200 {"database":"ok","redis":"ok"}   readiness; 503 if any fail
```

Liveness must not check dependencies. A brief Postgres blip should not cause the orchestrator to
kill and restart every API pod — that converts a recoverable dependency wobble into a full outage.
Readiness removes the pod from the load balancer, which is the correct response.

Workers expose readiness through the queue heartbeat rather than an HTTP endpoint.

## 16.8 Dashboards

Three, deliberately few:

**System health** — request rate, error rate, p50/p95/p99 latency, queue depth and wait, active
executions, DB pool, worker count. The one on the wall.

**Execution analytics** (in-product) — executions over time by status, top failing workflows,
duration distribution, node-type failure rates. Built with `recharts`, already installed.

**Agent cost** (in-product) — spend by day/model/agent, tokens, average iterations, per-run cost
distribution. This one gets looked at more than expected, because it maps directly to a bill.

## 16.9 Debugging a production incident

The intended path, which the instrumentation above is designed to support:

1. A user reports execution `019…` failed.
2. Open the execution detail — node status, error, and resolved parameters are usually enough.
3. If not: search logs by `execution_id`. Every line from that run, across api and workers, shares it.
4. If it looks systemic: check the system dashboard for the same window.
5. If it is a third party: `llm_errors_total` / `node_executions_total{node_type,status}` by type.
6. With tracing enabled, the trace shows exactly where the time went.

The design goal is that **step 2 resolves the majority of reports without server access**, which
is what keeps support load off engineering — and, not incidentally, is Persona A's stated pain in
[01](./01-product-overview.md) §1.5.
