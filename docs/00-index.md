# NeuroFlow — Design Documentation

> **Status:** Phase 0 — Research & Design. No production code written yet.
> **Audience:** Engineers implementing NeuroFlow, plus reviewers of the architecture.
> **Rule:** Implementation proceeds *from* this document set. If code and docs disagree,
> either fix the code or raise an ADR to change the doc — do not let them silently diverge.

---

## What this is

NeuroFlow is a self-hostable **visual workflow automation platform** (n8n-style node canvas)
with a first-class **visual AI agent builder** (comparable to OpenAI's Agent Builder) layered on
the same execution substrate. One graph engine, two authoring surfaces.

This folder is the complete design specification: product, architecture, data model, API
contracts, UI/UX system, security model, testing, deployment, and a phased roadmap.

---

## Reading order

New engineers should read `01` → `03` → `04`/`08` (depending on their side) → `10` → `11`.
Everything else is reference material consulted during implementation.

| # | Document | What it covers | ≈ Pages |
|---|---|---|---|
| 01 | [Product Overview](./01-product-overview.md) | Goals, users, use cases, competitive position, non-goals | 3 |
| 02 | [Current State Audit](./02-current-state-audit.md) | What exists in the repo today, dependency gap analysis | 3 |
| 03 | [System Architecture](./03-system-architecture.md) | Component map, process topology, request/execution lifecycles | 5 |
| 04 | [Frontend Architecture](./04-frontend-architecture.md) | Folder contract, layering rules, module anatomy, routing | 5 |
| 05 | [State Management & Data Fetching](./05-state-and-data-fetching.md) | Zustand store design, TanStack Query conventions, cache keys | 5 |
| 06 | [Canvas & Editor Design](./06-canvas-and-editor.md) | React Flow integration, node anatomy, interaction model | 6 |
| 07 | [UI/UX Design System](./07-ui-ux-design-system.md) | Visual language, tokens, motion, copy, accessibility | 5 |
| 08 | [Backend Architecture](./08-backend-architecture.md) | Layered MVC+service, module anatomy, DI, error handling | 5 |
| 09 | [Domain Modules](./09-domain-modules.md) | Per-module responsibilities, service contracts, boundaries | 5 |
| 10 | [Database Schema](./10-database-schema.md) | Entities, ER diagram, indexes, JSONB strategy, Alembic policy | 8 |
| 11 | [API Design](./11-api-design.md) | REST conventions, full endpoint list, request/response contracts | 6 |
| 12 | [Execution Engine](./12-execution-engine.md) | DAG scheduling, items, retries, suspension, expressions | 5 |
| 13 | [Node Catalog & Node SDK](./13-node-catalog-and-sdk.md) | Descriptor spec, built-in catalog, authoring a node | 5 |
| 14 | [Agent Builder](./14-agent-builder.md) | Agent graph semantics, tools, memory, guardrails, evals | 5 |
| 15 | [Security & Credentials](./15-security-and-credentials.md) | Threat model, RBAC, envelope encryption, SSRF, sandboxing | 6 |
| 16 | [Observability](./16-observability.md) | Structured logging, metrics, tracing, alerting, runbook path | 4 |
| 17 | [Testing Strategy](./17-testing-strategy.md) | Test pyramid, arch tests, contract tests, E2E, CI gates | 5 |
| 18 | [Deployment & Operations](./18-deployment-and-operations.md) | Docker/Compose, env matrix, deploys, scaling, backups | 5 |
| 19 | [Implementation Roadmap](./19-roadmap.md) | Phased milestones with acceptance criteria | 4 |
| 20 | [Architecture Decision Records](./20-adrs.md) | ADR-001..ADR-020, the "why" behind every hard call | 5 |
| 21 | [Glossary & Conventions](./21-glossary-and-conventions.md) | Vocabulary, naming, commit/branch/code style rules | 3 |

≈ **105 pages** — 36,000 words plus ~90 diagrams, schemas, and code specifications, at the
~350 words/page that this density of tables and code blocks actually renders to.

---

## The ten decisions that shape everything else

Full reasoning lives in [ADRs](./20-adrs.md); this is the summary a reader needs up front.

1. **One engine, two surfaces.** The agent builder is not a separate product. An agent is a
   workflow whose nodes happen to be LLM/tool/router nodes. Same executor, same run records,
   same logging. (ADR-001)
2. **The workflow graph is JSONB, not rows.** `workflow_versions.graph` holds `{nodes, edges}`.
   Node instances are never relational rows. Graphs are read and written whole; per-node
   queries are not a real access pattern. (ADR-004)
3. **Workflows are immutably versioned.** Editing produces a new `workflow_version`. An
   execution pins the exact version it ran, so history stays truthful forever. (ADR-005)
4. **Execution is async and out-of-process.** The API enqueues; a separate worker pool runs
   the DAG. The API never blocks on user workflow code. (ADR-007)
5. **Node types are declarative descriptors.** A node type is data (`NodeTypeDescriptor`) plus
   an `execute()` function. The frontend renders its parameter panel generically from the
   descriptor — adding a node requires zero frontend code. (ADR-011)
6. **Data flowing between nodes is a list of items**, `[{json, binary}]`, exactly like n8n.
   Fan-out is the natural consequence of a node returning N items. (ADR-008)
7. **Credentials are envelope-encrypted** with AES-256-GCM per-credential data keys wrapped by
   a master key. Plaintext secrets never leave the worker process and never enter a response
   body or a log line. (ADR-013)
8. **Server state lives in TanStack Query; client state lives in Zustand.** They never mirror
   each other. The one deliberate exception is the canvas editor draft. (ADR-016)
9. **Every backend module is a vertical slice** — `models / schemas / router / controller /
   service / repository`. Cross-module reads go through the other module's *service*, never its
   repository or its tables. (ADR-002)
10. **Expressions are a sandboxed mini-language**, not `eval`. `{{ $json.field }}` compiles to a
    restricted AST evaluated with no filesystem, network, or import access. (ADR-010)

---

## Document conventions

- **MUST / SHOULD / MAY** carry RFC-2119 weight. "MUST" items are CI-enforceable where possible.
- Code blocks are illustrative specifications, not copy-paste-ready source. They fix *shape*
  (names, types, signatures); the implementer fills in bodies.
- Diagrams are Mermaid so they render in GitHub, VS Code, and most doc viewers.
- `⚠️` marks a decision with real risk attached, where the alternative is defensible.
- `TODO(phase-N)` marks something deliberately deferred, with the phase that owns it.
