# 19 — Implementation Roadmap

Phases are ordered by **dependency and risk**, not by feature appeal. Each has an explicit exit
criterion that is demonstrable, not subjective — "the canvas feels good" is not an exit criterion;
"a user adds two nodes, connects them, saves, reloads, and the graph persists" is.

Durations assume 2–3 engineers. They are relative sizing, not commitments.

---

## Phase 0 — Design ✅ *(this document set)*

Repository audit, architecture, schema, API contracts, UI system, security model, roadmap.

**Exit:** an engineer can start Phase 1 without asking an architectural question.

---

## Phase 1 — Foundations *(~2 weeks)*

Nothing user-visible. Everything downstream depends on it.

**Risk spike first — before anything else:** React Flow v12 under React 19 `StrictMode`, 200 nodes,
drag/connect/undo. If it fails, decide React 18 pinning **now**, while it costs nothing.

**Backend.** Rewrite `requirements.txt` as UTF-8 and add the missing dependencies from
[02](./02-current-state-audit.md) §2.5. `app/` skeleton per [08](./08-backend-architecture.md).
`core/`: config, async database, redis, logging, exceptions, middleware, pagination. Alembic
initialised with the naming convention and the `citext`/`pg_trgm` extension migration. Health
endpoints. Docker + Compose. `ruff` + `mypy --strict` + `pytest` wired.

**Frontend.** Install zustand, TanStack Query, react-router, axios, zod, react-hook-form. Resolve
the `shadcn`/`@shadcn/react` dependency question from [02](./02-current-state-audit.md) §2.3.
Fill the folder skeleton with real `api/`, `config/`, `lib/`, `routing/`, `context/`. `AppProviders`,
`AppShell`, theme toggle, error boundary. Add the status/canvas tokens from
[07](./07-ui-ux-design-system.md) §7.2. ESLint boundary rules. Vitest + Playwright configured.

**CI.** Lint, type-check, unit tests, arch tests, build. Green on every PR from day one — a CI
pipeline added at month three never gets the same coverage.

**Exit:** `docker compose up` serves the app shell; a health check passes; CI is green;
migrations run up and down cleanly.

---

## Phase 2 — Identity & tenancy *(~2 weeks)*

`auth`, `users`, `organizations`, `projects` end to end, as the **reference implementation of the
module pattern** — every later module is copied from these, so they must be exemplary.

Registration, login, refresh rotation with reuse detection, password reset, API keys. RBAC matrix
and the `require()` helper. `audit` module. Frontend: auth pages, `AuthProvider`, route guards,
org/project switcher, members and settings pages.

**Exit:** a user signs up, gets a default org and project, invites a colleague with a role, and
that role is enforced — with the parameterised **tenant-isolation test suite** green
([17](./17-testing-strategy.md) §17.4). Ship the isolation tests in this phase; retrofitting them
later means auditing every query written in between.

---

## Phase 3 — The canvas *(~4 weeks — the biggest phase)*

The product becomes visible.

**Backend.** `workflows` module: CRUD, immutable versioning, graph validation, optimistic
concurrency (409), duplication, export/import. `nodes` module serving the registry. Node SDK base
classes and descriptor model ([13](./13-node-catalog-and-sdk.md)). Six nodes to prove the pattern:
Manual Trigger, Set, IF, HTTP Request, Code, No-Op.

**Frontend.** React Flow canvas with custom node components. Canvas store with undo/redo. Node
picker (`cmdk`). Generic descriptor-driven inspector with all field kinds. Expression editor with
Monaco, autocomplete, and preview. Insert-on-edge. Auto-layout. Workflow list page. Save with
conflict handling.

**Exit:** a user builds a 5-node workflow with expressions and branching, saves it, reloads, and
gets exactly what they built. Canvas interaction p95 < 100 ms at 150 nodes, verified.

---

## Phase 4 — Execution *(~3 weeks)*

The product becomes useful.

**Backend.** `app/engine/`: DAG construction, scheduler, item model, node runtime, error handling,
retries, sandboxed expression evaluator. `executions` module with payload offloading. arq worker.
Redis pub/sub → SSE endpoint. Code node subprocess sandbox. Recovery sweeper and watchdog.

**Frontend.** Run button with live canvas status. Executions list and detail. `DataView`
(table/JSON/schema/binary). Per-node input/output panels. Live log streaming. Retry from failed
node. Pinned data.

**Exit:** **UC-1 works end to end.** A manual run executes, streams status to the canvas, persists
per-node data, and a deliberate failure is diagnosable purely from the UI.

---

## Phase 5 — Triggers & credentials *(~3 weeks)*

The product runs unattended — the threshold at which it is genuinely adopted.

**Backend.** `credentials` module with envelope encryption, credential type descriptors,
declarative auth injection, OAuth2 flows, connection testing. `webhooks` with signature
verification and response modes. `schedules` with the lock-guarded scheduler process. Suspension
and resume (Wait node). Sub-workflow execution. `variables`.

**Frontend.** Credential list, dynamic create form, OAuth connect flow, credential picker in the
inspector. Webhook URL display with test mode. Schedule configuration UI. Workflow activation
toggle.

**Exit:** **UC-2 and UC-3 work.** A webhook from a real third-party service triggers a production
workflow using a stored credential; a scheduled workflow fires on time; an approval workflow
suspends and resumes. **The secret-leak sentinel test passes.**

---

## Phase 6 — Node catalog *(~4 weeks, parallelisable)*

Breadth. Highly parallel across engineers once the SDK is stable — this is the phase where team
size actually helps.

All remaining core, flow, and data nodes from [13](./13-node-catalog-and-sdk.md) §13.5. The
first ~20 integrations. Pagination and batching helpers. Registry conformance tests. Node
documentation generated from descriptors.

**Exit:** 25+ node types, each with unit tests, a recorded integration test, and a
conformance-passing descriptor. Adding a node touches exactly one backend file.

---

## Phase 7 — Agents *(~4 weeks)*

The differentiator. Deliberately last, because it rests on everything before it — and it is only
cheap *because* of that ordering.

**Backend.** Provider abstraction (Anthropic, OpenAI, Google, Ollama) over `httpx`. Agent loop with
tool calling, budget enforcement, and stop reasons. Four tool kinds — the workflow tool is the
important one. Memory backends. Guardrails. `agents` module with versions, runs, message traces,
and cost accounting. Streaming chat endpoint. Eval harness.

**Frontend.** Agent canvas mode with sub-ports. Model, tool, and memory configuration. Chat test
panel with live trace (built on the already-installed `message`/`bubble` primitives). Run history
with token and cost breakdown. Eval runner with version comparison. Cost dashboard.

**Exit:** **UC-4 works.** An agent with three tools handles a support ticket, the trace shows every
tool call with timing and cost, and an eval suite runs against two versions with a comparable
pass rate.

---

## Phase 8 — Production hardening *(~3 weeks)*

The gap between "demo" and "deployable".

Execution retention and table partitioning. Full Prometheus metrics and dashboards. OpenTelemetry
tracing. Rate limiting everywhere. Performance work against the [03](./03-system-architecture.md)
§3.8 budgets. Accessibility audit and fixes. Empty/loading/error states audited against the
[07](./07-ui-ux-design-system.md) §7.12 polish checklist. Onboarding and templates. Self-host
documentation and upgrade guide. **External security review.**

**Exit:** all four core use cases demonstrable on a fresh install by someone who read only the
in-app onboarding; performance budgets met; security review findings closed.

---

## Post-v1

Ordered by expected value, not by enthusiasm:

| Item | Why it waits |
|---|---|
| SSO/OIDC | Blocks enterprise deals; not needed to prove the product |
| Multiplayer canvas editing | Large (CRDT); genuinely wanted only after teams are on it |
| Table partitioning at scale | Needed before ~10M executions, not before that |
| Community node registry | Big security surface (non-goal N2) |
| Visual debugger with breakpoints | Pin data covers ~90% at ~10% of cost (non-goal N4) |
| Postgres RLS defence-in-depth | Pooling interaction needs design work |
| Embedded/white-label SDK | Different product shape (non-goal N5) |
| Workflow templates marketplace | Needs a user base first |
| Mobile monitoring app | Read-only; genuinely useful but not core |

---

## Sequencing risks

**The three that can actually derail this:**

1. **React Flow on React 19.** Gates Phase 3, which gates everything. Spike in week 1 of Phase 1.
2. **The descriptor-driven inspector.** If it cannot express real nodes' parameter complexity,
   every node needs custom UI and the catalog phase multiplies in size. Validate it against the
   *hardest* node (HTTP Request, with its ~40 conditional parameters) in Phase 3, not the easiest.
3. **Execution data volume.** If payload offloading is deferred, the first real workload fills the
   database and the fix is a painful migration under pressure. Build it in Phase 4 as specified,
   not "when it becomes a problem".

**Deliberate sequencing choices worth defending:**

- **Agents last.** Tempting to build early because it is the differentiator; it would be built
  twice, since it depends on execution, credentials, and the node SDK.
- **Tenancy in Phase 2, not later.** Retrofitting multi-tenancy is one of the most expensive
  migrations in software, and the isolation tests must be written alongside the first queries.
- **CI in Phase 1.** A pipeline added later never reaches the same coverage, and the arch tests in
  particular only work if they were never allowed to fail.
