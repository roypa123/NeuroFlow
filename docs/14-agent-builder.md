# 14 — Agent Builder

The second authoring surface, and the product's main differentiator. This document specifies what
an agent *is* in NeuroFlow, how it is authored, and how it executes.

## 14.1 The core claim

**An agent is a workflow.** Specifically: a graph whose central node is an LLM that loops,
choosing tools until it produces a final answer. Everything the workflow engine already
provides — execution records, per-step data inspection, retries, credentials, streaming logs,
sub-workflows — applies unchanged.

What the agent builder adds is not a second engine. It is:

1. A **canvas mode** tuned to agent shapes (model, tools, memory as attached sub-nodes rather than
   sequential steps).
2. A **compiler** from agent config to a workflow graph.
3. **Agent-specific run records** — message traces, tool calls, token counts, cost.
4. A **chat test panel** with streaming and an eval harness.

If this claim ever stops holding — if agents need their own scheduler — that is an architectural
regression worth an ADR, not a quiet fork. (ADR-001)

## 14.2 Why not a separate agent runtime

The alternative is a bespoke agent service with its own execution model. Rejected because it
immediately duplicates: credentials, retries, logging, streaming, versioning, permissions, and the
executions UI. Two of everything, drifting apart, forever. The complexity of compiling agent
config into a graph is much smaller than the complexity of maintaining two runtimes — and the
compile step buys a genuine feature: **an agent can be dropped into a larger workflow as a node.**

That is the composition story competitors mostly lack, and it falls out of this decision for free.

## 14.3 The agent canvas

Visually distinct from the workflow canvas, because agent topology is not sequential:

```
                        ┌──────────────────┐
     input ────────────▶│                  │────────▶ output
                        │   AI Agent       │
                        │   "Support bot"  │
                        └──┬────┬───────┬──┘
                    model  │    │ tools │  memory
                        ▲  │    │   ▲   │     ▲
              ┌─────────┴┐ │  ┌─┴───┴─┐ │ ┌───┴──────┐
              │ Claude   │ │  │ 3 tools│ │ │ Postgres │
              │ Opus 5   │ │  └────────┘ │ │ memory   │
              └──────────┘ │             │ └──────────┘
                           ▼             ▼
```

The agent node has **sub-ports on its bottom edge** — `model`, `tools`, `memory`, `guardrails` —
each accepting a specific node kind. Connection validation ([06](./06-canvas-and-editor.md) §6.6)
enforces the types, so a Postgres node cannot land on the `model` port.

This is a stronger idea than a sequential representation: it shows *composition* (this agent has
these capabilities) rather than *sequence* (which is what a loop obscures anyway). Tools attached
downward read as an inventory, which is exactly the right mental model.

**Two modes on the same canvas.** A workflow can contain an Agent node; an agent graph is a
workflow graph. Switching modes changes the palette and the default layout direction, not the
document.

## 14.4 Agent configuration

```jsonc
{
  "name": "Support triage",
  "model": {
    "provider": "anthropic",
    "model": "claude-opus-5",
    "temperature": 0.2,
    "maxTokens": 4096,
    "credentialId": "019…"
  },
  "instructions": "You are a support triage assistant for Acme…\n{{ $json.context }}",
  "tools": [
    { "type": "workflow", "name": "search_docs",  "workflowId": "019…",
      "description": "Search the product documentation. Use for how-to questions.",
      "schema": { "type": "object", "properties": { "query": { "type": "string" } },
                  "required": ["query"] } },
    { "type": "http", "name": "lookup_order", "credentialId": "019…",
      "description": "Look up an order by id.",
      "request": { "method": "GET", "url": "https://api.acme.com/orders/{{ $tool.orderId }}" },
      "schema": { "type": "object", "properties": { "orderId": { "type": "string" } },
                  "required": ["orderId"] } },
    { "type": "agent", "name": "escalate", "agentId": "019…",
      "description": "Hand off to the escalation specialist agent." }
  ],
  "memory": { "type": "postgres", "sessionKey": "={{ $json.conversationId }}", "windowSize": 20 },
  "outputSchema": { "type": "object",
                    "properties": { "category": { "type": "string" },
                                    "priority": { "enum": ["low","medium","high"] },
                                    "reply": { "type": "string" } },
                    "required": ["category","priority","reply"] },
  "guardrails": {
    "input":  [{ "type": "pii_check", "action": "redact" }],
    "output": [{ "type": "content_filter", "action": "block" },
               { "type": "schema_validate", "action": "retry", "maxRetries": 2 }]
  },
  "limits": { "maxIterations": 10, "maxTokens": 50000, "maxCostMicros": 500000,
              "timeoutSeconds": 120 }
}
```

`limits` is not optional and has non-null defaults. **An agent without a cost ceiling is an
unbounded bill**, and the failure mode — a tool that returns an error the model retries forever —
is common enough that it must be structurally prevented, not documented.

## 14.5 The agent loop

```python
async def run_agent(config: AgentConfig, input: dict, ctx: ExecutionContext) -> AgentResult:
    messages = await memory.load(config.memory, input)
    messages.append(Message(role="user", content=render(input)))
    await guardrails.check_input(messages, config.guardrails.input)

    for iteration in range(config.limits.max_iterations):
        ctx.check_budget(config.limits)                 # tokens, cost, wall clock

        response = await provider.chat(
            model=config.model, messages=messages,
            tools=[t.to_schema() for t in config.tools],
            response_format=config.output_schema,
        )
        await ctx.record_message(response)              # persisted to agent_messages

        if not response.tool_calls:
            result = await guardrails.check_output(response, config.guardrails.output)
            await memory.save(config.memory, messages + [response])
            return AgentResult(output=result, iterations=iteration + 1,
                               stop_reason="completed")

        # Tool calls execute in parallel — they are independent by construction
        results = await asyncio.gather(*[
            execute_tool(config.tools_by_name[c.name], c.arguments, ctx)
            for c in response.tool_calls
        ], return_exceptions=True)

        messages.append(response)
        messages.extend(tool_result_messages(response.tool_calls, results))

    return AgentResult(stop_reason="max_iterations", output=None)
```

**Tool errors are fed back to the model as tool results, not raised.** A 404 from `lookup_order`
should let the agent say "I couldn't find that order" rather than crashing the execution. Only
infrastructure failures (auth, budget exceeded, timeout) terminate the run.

Every iteration writes an `agent_messages` row, so the trace is complete even for a run that
crashed halfway. Reconstructing a trace from provider logs after the fact is not possible.

## 14.6 Tools

Four kinds, all reduced to a JSON-schema function the model can call:

| Kind | What it does | When to use |
|---|---|---|
| **Workflow tool** | Runs another NeuroFlow workflow as a sub-execution | Complex multi-step capabilities; fully observable |
| **HTTP tool** | One declarative HTTP call with a credential | Simple API lookups |
| **Code tool** | Sandboxed JS | Computation, formatting, math |
| **Agent tool** | Calls another agent | Handoffs, specialist delegation |

The **workflow tool is the strategic one.** It means every integration in the node catalog is
automatically available to agents, without writing a single agent-specific connector. A user who
has built a "create Jira ticket" workflow has, for free, given every agent a `create_jira_ticket`
tool. That leverage is the reason the compile-to-workflow decision pays for itself.

**Tool descriptions are prompt engineering, not documentation.** The UI should say so explicitly,
because a vague description is the single most common cause of an agent that "won't use its
tools." The builder shows a warning when a description is under ~20 characters or duplicates
another tool's.

Sub-workflow tool calls appear as **nested executions** in the UI, so a tool that misbehaves is
debugged with the same data panel as anything else.

## 14.7 Memory

| Type | Storage | Use |
|---|---|---|
| None | — | Stateless classification/extraction — the correct default |
| Buffer window | In execution | Single multi-turn run |
| Postgres | `agent_messages` keyed by session | Persistent conversations |
| Summary | Postgres + periodic LLM summarisation | Long conversations past the context window |
| Vector | pgvector | Semantic recall over history |

`sessionKey` is an expression (`={{ $json.conversationId }}`), which is what allows one agent to
serve thousands of independent conversations. **Getting this wrong leaks one user's conversation
into another's**, so the builder warns loudly if `sessionKey` is a constant.

## 14.8 Guardrails

Input guardrails run before the model, output guardrails before returning:

| Guardrail | Actions |
|---|---|
| PII detection | redact / block / warn |
| Content filter | block / flag |
| Schema validation | retry with the validation error appended / block |
| Max length | truncate / block |
| Custom (workflow) | any workflow returning `{allowed, reason}` |

Schema-validate-with-retry is the highest-value one in practice: feeding the validation error back
to the model recovers a malformed structured output most of the time, and turns a hard failure
into a 1-second retry.

Guardrail decisions are recorded in the trace. A blocked output that leaves no record is
indistinguishable from a bug.

## 14.9 The test panel

Where agent iteration actually happens — this surface is used more than the canvas:

```
┌────────────────────────────┬─────────────────────────────┐
│ Chat                       │ Trace                       │
│ ┌────────────────────────┐ │ ▸ user: "Where is order…"   │
│ │ user: Where is my      │ │ ▾ assistant → tool_call     │
│ │ order #4821?           │ │     lookup_order            │
│ └────────────────────────┘ │     { "orderId": "4821" }   │
│ ┌────────────────────────┐ │   ⚙ tool: 240ms · 200 OK    │
│ │ assistant: Order #4821 │ │     { "status": "shipped" } │
│ │ shipped Tuesday…       │ │ ▾ assistant: final          │
│ └────────────────────────┘ │                             │
│ [ message…          ] Send │ 2 iterations · 1,284 tok    │
│                            │ $0.0031 · 1.8s              │
└────────────────────────────┴─────────────────────────────┘
```

Built on the `message`, `message-scroller`, `bubble`, and `attachment` primitives that are
**already installed** — an unusually lucky fit with the existing component set.

Streaming via SSE (`POST /agents/{id}/chat`): tokens stream as they arrive, tool calls appear the
moment they are requested, and results fill in when they return. Watching a tool call resolve in
real time is what makes an agent's behaviour legible.

Every test run shows **cost and token count**, always visible. Cost that is hidden during
development is discovered in the monthly bill.

## 14.10 Evaluation

Without evals, agent development is vibes. The harness is deliberately minimal and shipped early:

```jsonc
{
  "name": "Triage accuracy",
  "cases": [
    { "input": { "ticket": "My card was charged twice" },
      "expected": { "category": "billing", "priority": "high" },
      "assertions": [
        { "type": "json_path_equals", "path": "$.category", "value": "billing" },
        { "type": "llm_judge", "criteria": "The reply acknowledges the double charge" },
        { "type": "tool_called", "tool": "lookup_order" },
        { "type": "max_cost_micros", "value": 5000 }
      ] }
  ]
}
```

Runs all cases in parallel against a pinned agent version and reports pass rate, cost, latency, and
a per-case diff. Comparing two versions side by side is the primary workflow — "did my prompt
change help?" is otherwise unanswerable.

Assertion types: `equals`, `contains`, `json_path_equals`, `regex`, `tool_called`,
`tool_not_called`, `max_iterations`, `max_cost_micros`, `schema_valid`, `llm_judge`.

## 14.11 Provider abstraction

```python
class ChatProvider(Protocol):
    async def chat(self, *, model: str, messages: list[Message],
                   tools: list[ToolSchema] | None = None,
                   response_format: dict | None = None,
                   stream: bool = False) -> ChatResponse | AsyncIterator[ChatChunk]: ...
```

Implementations over `httpx`: Anthropic, OpenAI, Google, Azure OpenAI, Ollama, plus an
OpenAI-compatible generic adapter that covers most self-hosted gateways.

**No vendor SDKs** (ADR-014). SDKs bring dependency weight, differing async semantics, and their
own retry logic that fights ours. A chat-completions HTTP call is small; the abstraction is worth
more than the SDK.

The provider layer normalises: tool-call formats, streaming chunk shapes, token usage fields,
error taxonomies (rate limit vs. context length vs. content filter), and retry semantics. A model
registry holds context windows, capabilities, and per-token pricing so cost is computed at write
time and stays historically accurate.

## 14.12 Cost control

Enforced at four levels, because any single one can be bypassed:

1. **Per run** — `maxCostMicros`, `maxTokens`, `maxIterations` in the agent config.
2. **Per workflow** — an execution-wide cost ceiling.
3. **Per project** — a monthly budget with alerting, then hard-stop.
4. **Per org** — a global cap.

Every LLM call records prompt/completion tokens and computed cost on the `agent_messages` row.
The dashboard breaks spend down by agent, model, and day using `recharts` (already installed).

⚠️ Cost enforcement is **pre-flight where possible**: estimate the prompt's token count before the
call and refuse if the estimate would exceed the remaining budget. Checking only after the
response has already been paid for is closing the door after the bill.
