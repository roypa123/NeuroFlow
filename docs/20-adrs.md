# 20 — Architecture Decision Records

Each record states the decision, the alternatives seriously considered, and the consequences we
accept. An ADR is not changed once accepted; it is **superseded** by a new one, so the reasoning
trail survives.

Format: **Context → Decision → Alternatives → Consequences.**

---

## ADR-001 — Agents and workflows share one execution engine

**Context.** Agents could be a separate subsystem with their own runtime, or a compilation target
for the existing graph engine.

**Decision.** An agent compiles to a workflow graph and runs on the same engine, storage, and UI.

**Alternatives.** A dedicated agent service — rejected because it duplicates credentials, retries,
logging, streaming, versioning, permissions, and the executions UI, and the two copies drift.

**Consequences.** Agent features arrive faster than the effort suggests, because they inherit the
platform. Agents compose into workflows as nodes for free, which is a genuine differentiator.
The cost is a compile step and a constraint: an agent capability that cannot be expressed as a
graph needs an ADR, not a fork. ⚠️ Watch for engine features added *only* for agents — that is the
early signal this decision is failing.

---

## ADR-002 — Modular monolith, not microservices

**Context.** The system has clear domain boundaries that could be separate services.

**Decision.** One deployable, internally split into vertical modules with enforced import
boundaries.

**Alternatives.** Microservices — rejected: at this team size the distributed-transaction,
deployment, and debugging costs dwarf the benefits. Serverless — rejected: long-running executions
fit it badly.

**Consequences.** Simple local development, transactional consistency, one deploy. If a module
ever needs independent scaling, the enforced boundaries make extraction mechanical. The risk is
boundary erosion, which is why `import-linter` runs in CI rather than being a convention.

---

## ADR-003 — UUIDv7 primary keys

**Decision.** UUIDv7 for all primary keys.

**Alternatives.** Auto-increment integers — rejected: enumerable in URLs, painful to merge across
environments during import/export. UUIDv4 — rejected: random ordering causes B-tree page splits
and index bloat on high-write tables like `node_executions`.

**Consequences.** Time-ordered inserts (fast, like sequential integers), non-enumerable, and
client-generatable. Cost: 16 bytes vs 8, and IDs are not human-quotable — accepted.

---

## ADR-004 — The workflow graph is a JSONB document

**Decision.** `workflow_versions.graph` stores `{nodes, edges, viewport}` as JSONB. Node instances
are not relational rows.

**Alternatives.** Relational `nodes`/`edges` tables — rejected for four reasons: the access pattern
is always the whole graph; versioning becomes a deep copy with ID remapping instead of one row;
parameters are heterogeneous and would be JSONB anyway; the client's model already *is*
`{nodes, edges}`.

**Consequences.** Reading a workflow is one row. Versioning is trivial. Cross-workflow node queries
need JSONB operators plus a GIN index — acceptable, since those are analytics, not hot path.
⚠️ Referential integrity between a node's `credentialId` and the `credentials` table cannot be a
foreign key; it is validated in the service layer and by a periodic consistency check.

---

## ADR-005 — Immutable workflow versioning

**Decision.** Every save creates a new immutable `workflow_version`. Executions pin a version id.

**Alternatives.** Mutating the workflow row with an audit log — rejected: a past execution could
not be reproduced or even correctly displayed.

**Consequences.** Truthful history forever; free rollback; safe concurrent editing via optimistic
concurrency. Cost: table growth (mitigated by dedupe-on-checksum for no-op saves and pruning of
versions with no executions), and renaming a node must rewrite expressions across the graph.

---

## ADR-006 — REST + SSE, not GraphQL

**Decision.** REST/JSON for CRUD; SSE for live execution events.

**Alternatives.** GraphQL — rejected: the client's needs are well-known and stable, so the flexibility
buys little, while N+1 risk, caching complexity, and authorization-per-field cost a lot. tRPC —
rejected: couples the API to a TypeScript client, and we want a public API for Persona B.

**Consequences.** Cacheable, debuggable, curl-able, OpenAPI for free. Some over-fetching, mitigated
by distinct `ListItem` vs `Read` schemas.

---

## ADR-007 — arq on Redis for the job queue

**Decision.** `arq` for async job processing.

**Alternatives.** Celery — rejected: sync-first, heavy, and its async support is bolted on, which
fights an all-async codebase. RQ — sync-only. Postgres-as-queue (`SKIP LOCKED`) — genuinely
attractive for the reduced dependency count, rejected because Redis is already needed for pub/sub
and rate limiting, and polling Postgres adds load to the most contended component.

**Consequences.** Small, async-native, few dependencies. Cost: a smaller ecosystem than Celery and
no built-in workflow primitives (chords/chains) — which we do not need, since the engine *is* the
workflow layer.

---

## ADR-008 — Data flows as a list of items

**Decision.** Node-to-node data is `list[Item]` where `Item = {json, binary, pairedItem}`.

**Alternatives.** A single JSON object per node — simpler, but forces users to write explicit loops
for the most common operation there is.

**Consequences.** Automatic fan-out; one uniform data-inspection UI; expressible provenance. Cost:
node authors must think in items, and the "which item am I looking at?" question needs good UI
answers. Precedent (n8n) shows both are manageable.

---

## ADR-009 — Payload offloading above 64 KB

**Decision.** Execution payloads under 64 KB are inline JSONB; larger ones go to object storage
with only a key in Postgres. Hard cap 16 MB, then truncation with a flag.

**Alternatives.** Everything in Postgres — rejected: the first file-downloading workflow turns the
primary database into a file server. Everything in object storage — rejected: an extra network
round trip to view a 200-byte payload makes the UI feel slow.

**Consequences.** The database stays small and fast; large binaries are cheap. Cost: two storage
paths, and an object-store dependency for the large case (degrading gracefully to inline-only when
unconfigured). Orphaned objects are reaped by the retention job.

---

## ADR-010 — Expressions are a sandboxed AST interpreter

**Decision.** `{{ }}` expressions compile to a restricted AST evaluated with an allow-listed scope,
a 100 ms CPU budget, and no I/O.

**Alternatives.** `eval` with a restricted globals dict — rejected: every published Python sandbox
of this kind has been escaped, usually via attribute traversal. A full embedded language (Lua,
Starlark) — rejected as too heavy and unfamiliar for one-line expressions.

**Consequences.** Safe, fast, predictable. Cost: we implement and maintain a small language, and
users cannot do arbitrary computation in an expression — which is what the Code node is for.

---

## ADR-011 — Node types are declarative descriptors

**Decision.** A node is a `NodeTypeDescriptor` plus `execute()`. The frontend renders every
parameter panel generically.

**Alternatives.** Per-node React components — rejected: adding a node would require frontend work,
a release, and design review, capping the catalog at what one team can hand-build.

**Consequences.** A new node is one backend file, no frontend change, no migration. Cost: the
descriptor system must be expressive enough for genuinely complex nodes, which is why it is
validated against HTTP Request (the hardest one) early in Phase 3. ⚠️ The first bespoke node panel
breaks this decision; it should require an ADR.

---

## ADR-012 — React Flow for the canvas

**Decision.** `@xyflow/react` v12.

**Alternatives.** Hand-rolled SVG/canvas — months of undifferentiated work with a poor
accessibility story. Konva/PixiJS — rejected: losing DOM nodes means re-implementing forms, focus,
and text selection inside a canvas, which is a bad trade for a form-heavy product.

**Consequences.** Weeks saved; DOM nodes keep shadcn components usable inside a node. Cost: a
dependency in the most critical path, and known performance pitfalls (inline `nodeTypes`, broad
subscriptions) that [06](./06-canvas-and-editor.md) §6.12 addresses explicitly.
⚠️ React 19 compatibility is the project's top technical risk; spike it first.

---

## ADR-013 — Envelope encryption for credentials

**Decision.** AES-256-GCM with a per-credential data key wrapped by a master key held outside the
database, with `key_version` for rotation.

**Alternatives.** Encrypt directly with the master key — rejected: rotation requires decrypting and
re-encrypting every secret, so nobody ever rotates. Store in an external vault only — rejected:
conflicts with the one-command self-host goal, though the design permits it as an option.

**Consequences.** Rotation is a cheap background re-wrap; blast radius is one credential per leaked
DEK; KMS migration is a config change. Cost: more moving parts, and **losing the master key loses
every credential** — which must be documented loudly rather than quietly.

---

## ADR-014 — No vendor LLM SDKs

**Decision.** Providers are thin adapters over `httpx` implementing one `ChatProvider` protocol.

**Alternatives.** Official SDKs per provider — rejected: dependency weight, divergent async
semantics, and their own retry logic fighting ours. LangChain — rejected: a large abstraction we
would fight more than use, given we already own the graph layer.

**Consequences.** Adding a provider adds no dependency; retries, timeouts, and observability are
uniform. Cost: we track provider API changes ourselves — bounded, since chat-completions endpoints
are stable and small.

---

## ADR-015 — SSE, not WebSockets, for execution streaming

**Decision.** Server-Sent Events over `GET /executions/{id}/stream`.

**Alternatives.** WebSockets — rejected for v1: the data flow is one-directional, so the added
complexity (auth handshake, proxy configuration, reconnection logic, sticky sessions) buys nothing.
Polling — rejected: either too slow or too expensive.

**Consequences.** Plain HTTP, automatic reconnection with `Last-Event-ID`, works through ordinary
proxies, and any API replica can serve any stream because fan-out happens in Redis. Cost: the
browser's six-connections-per-host limit (mitigated by HTTP/2 and by closing streams on
completion), and no client→server channel — which is exactly why WebSockets remain reserved for
Phase 5 multiplayer editing.

---

## ADR-016 — TanStack Query for server state, Zustand for client state

**Decision.** Strict split; neither mirrors the other.

**Alternatives.** Redux Toolkit for everything — rejected: with server state removed, the remaining
state is small and canvas-shaped, and RTK's boilerplate buys nothing at that size. Zustand alone —
rejected: re-implementing caching, deduplication, and background refetch, worse.

**Consequences.** Each library does what it is good at; no cache/store drift. Cost: two mental
models, and one documented exception (the canvas draft, [05](./05-state-and-data-fetching.md) §5.6)
that must be understood rather than "corrected".

---

## ADR-017 — A `store/` folder, deviating from the brief's layout

**Context.** The brief lists `context/` but no state folder.

**Decision.** Add `src/store/` for Zustand stores. `context/` holds only genuine React providers.

**Alternatives.** Stores inside `context/` — rejected: Zustand's defining property is that it does
*not* use context, so co-locating them guarantees confusion about which mechanism owns what.

**Consequences.** One additive deviation from the brief, documented here. Every other folder in the
brief is honoured exactly.

---

## ADR-018 — Hand-written zod schemas, not generated API types

**Decision.** The frontend defines zod schemas mirroring API contracts and validates at the
boundary.

**Alternatives.** Generate TypeScript from OpenAPI — rejected for v1: generated types are
structurally correct but semantically weak (everything optional becomes `| undefined`), they carry
no runtime validation, and the generator becomes a build-order dependency between two CI pipelines.

**Consequences.** Runtime validation catches contract drift at the exact boundary with a clear
error. Cost: schemas are written twice, in two languages. Mitigated by the fixture-based contract
test in [17](./17-testing-strategy.md) §17.8. ⚠️ Revisit if drift becomes a recurring incident
rather than a hypothetical one.

---

## ADR-019 — camelCase on the wire, snake_case in Python

**Decision.** Pydantic `alias_generator=to_camel` with `populate_by_name=True`.

**Alternatives.** snake_case on the wire — idiomatic for the backend, un-idiomatic for every
JavaScript consumer. Conversion in the frontend — rejected: it obscures the network payload in
DevTools, which is where people debug.

**Consequences.** Both languages stay idiomatic for one config line. The rule must be applied from
the very first endpoint — mixed conventions are far worse than either choice.

---

## ADR-020 — Postgres-only for vector storage in v1

**Decision.** `pgvector` for embeddings; no dedicated vector database.

**Alternatives.** Pinecone/Weaviate/Qdrant — rejected for v1: another service to deploy, back up,
and secure, conflicting with the one-command self-host goal, for a scale most users will not reach.

**Consequences.** One database to operate; vectors participate in normal transactions and backups.
Cost: pgvector is slower than a dedicated store above roughly 10M vectors. The Vector Store node's
interface is deliberately provider-agnostic, so adding an external backend later is a new node
implementation, not a redesign.
