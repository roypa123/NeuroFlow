# 21 — Glossary & Conventions

## 21.1 Domain vocabulary

These words have exact meanings. Using them loosely in code, UI copy, or discussion is how a
codebase ends up with `flow`, `pipeline`, `job`, and `run` all meaning the same thing.

| Term | Meaning |
|---|---|
| **Workflow** | A named, versioned graph of nodes belonging to a project |
| **Workflow version** | An immutable snapshot of a workflow's graph. Executions pin one |
| **Graph** | `{nodes, edges, viewport}` — the JSONB document |
| **Node** | An instance *in* a graph (has an id, a name, parameters, a position) |
| **Node type** | The *kind* of node (`neuroflow.http`), defined by a descriptor |
| **Descriptor** | The declarative definition of a node type, driving the UI |
| **Port / Handle** | A connection point. Port is the model; handle is the rendered UI |
| **Edge / Connection** | A link from one node's output port to another's input port |
| **Trigger** | A node that starts an execution (webhook, schedule, manual) |
| **Execution** | One run of one workflow version |
| **Node execution** | One run of one node within an execution (`run_index` for loops) |
| **Item** | The unit of data: `{json, binary, pairedItem}` |
| **Fan-out** | One node emitting N items, causing downstream nodes to process N |
| **Expression** | `{{ … }}` in a parameter, evaluated at execution time |
| **Credential** | Encrypted third-party secret, referenced by nodes, never readable |
| **Agent** | A workflow whose core node is an LLM that loops over tools |
| **Tool** | A capability exposed to an agent as a JSON-schema function |
| **Agent run** | One agent invocation, with a message trace and cost |
| **Iteration** | One model call + tool round inside an agent run |
| **Pinned data** | Frozen sample output used in editor runs only, never in production |
| **Project** | Grouping of workflows/agents/credentials within an organization |
| **Organization** | The tenancy root |

**Terms we deliberately do not use:** *pipeline* (means "workflow"), *job* (means "execution" —
`job` is reserved for the arq queue entry), *flow* (ambiguous between workflow and control flow),
*step* (means "node"), *task* (unused entirely).

## 21.2 Naming conventions

### Backend (Python)

| Thing | Convention | Example |
|---|---|---|
| Module | `snake_case`, singular domain | `app/modules/workflow/` → **plural**: `workflows/` |
| Class | `PascalCase` | `WorkflowService`, `NodeTypeDescriptor` |
| Function / variable | `snake_case` | `update_graph`, `execution_id` |
| Constant | `SCREAMING_SNAKE` | `MAX_ITEMS_PER_NODE` |
| Private | leading underscore | `_session`, `_handle_error` |
| Table | plural snake_case | `workflow_versions` |
| FK column | `<singular>_id` | `workflow_id` |
| Boolean column | `is_` / `has_` | `is_active` |
| Timestamp column | `_at` suffix | `created_at`, `deleted_at` |
| Pydantic schema | `<Resource><Verb>` | `WorkflowCreate`, `WorkflowRead` |
| Exception | `<Thing><Problem>` | `WorkflowNotFound` |
| Test | `test_<subject>_<condition>_<expectation>` | `test_update_graph_rejects_stale_version` |

### Frontend (TypeScript)

| Thing | Convention | Example |
|---|---|---|
| Component file | `PascalCase.tsx` | `WorkflowCard.tsx` |
| Non-component file | `kebab-case.ts` | `use-debounce.ts`, `query-client.ts` |
| Component | `PascalCase` | `NodeInspector` |
| Hook | `useX` | `useWorkflow`, `useExecutionStream` |
| Type / interface | `PascalCase`, no `I` prefix | `Workflow`, not `IWorkflow` |
| Zod schema | `camelCase` + `Schema` | `workflowSchema` |
| Constant | `SCREAMING_SNAKE` | `MAX_CANVAS_NODES` |
| Event handler prop | `onX`; internal handler `handleX` | `onSelect` / `handleSelect` |
| Boolean | `is` / `has` / `should` | `isDirty`, `hasUnsavedChanges` |
| Query key factory | `<domain>Keys` | `workflowKeys` |

**Node type keys** are `neuroflow.<name>` in `camelCase` (`neuroflow.httpRequest`), permanently
stable — they are stored in every customer's saved graphs ([13](./13-node-catalog-and-sdk.md) §13.2).

## 21.3 Code style

**Python.** `ruff format` (88 cols) and `ruff check` with `E,F,I,N,UP,B,S,A,C4,PT,SIM,RET,ARG,PTH`.
`mypy --strict`. Every public function is fully annotated; `Any` requires a comment justifying it.
Docstrings on every service method — one line of *why*, not a restatement of the signature.
Prefer `pathlib` over `os.path`, dataclasses/Pydantic over dicts for structured data, and early
returns over nesting.

**TypeScript.** ESLint with `typescript-eslint` recommended-type-checked, plus `react-hooks`,
`react-refresh`, `boundaries`, and `consistent-type-imports` (autofix on). Prettier at 100 cols.
`any` is an error; `unknown` + zod is the escape hatch. No default exports except route-level lazy
pages. **No TS enums** (`erasableSyntaxOnly` bans them) — `as const` arrays plus a union type, per
[04](./04-frontend-architecture.md) §4.7.

**Comments.** Explain *why*, never *what*. A comment restating the code is deleted in review. The
comments that earn their place: non-obvious business rules, workarounds with a linked issue,
performance-critical choices, and security-relevant invariants.

## 21.4 Git conventions

**Branches:** `<type>/<short-description>` — `feat/agent-tool-picker`, `fix/sse-reconnect-leak`,
`chore/bump-fastapi`, `docs/execution-engine`.

**Commits:** Conventional Commits.

```
feat(workflows): add optimistic concurrency to graph updates

Returns 409 with the actual version id when base_version_id is stale,
so the client can offer reload-or-overwrite without a second request.

Closes #142
```

Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `build`, `ci`.
Scopes match module names (`workflows`, `executions`, `canvas`, `agents`, `engine`).

**Pull requests.** Small enough to review properly — under ~400 changed lines wherever possible.
The description states what changed, why, and how it was verified. Screenshots for UI changes, in
**both themes**. The [07](./07-ui-ux-design-system.md) §7.12 polish checklist for user-facing work
and the [15](./15-security-and-credentials.md) §15.12 checklist where security surfaces are
touched. Squash merge; the PR title becomes the commit message.

## 21.5 Review checklist

Ordered by how often each catches something real:

1. **Does it do what the description says**, and only that?
2. **Layering** — logic in components? SQL outside a repository? `HTTPException` in a service?
3. **Tenant scoping** — is every new query filtered by org/project?
4. **Secrets** — can any new code path log, return, or persist a credential value?
5. **Error handling** — what happens when the network call fails, the list is empty, the value is null?
6. **Tests** — do they assert behaviour, and would deleting them let a real bug through?
7. **Naming** — does it match §21.1 and §21.2?
8. **Migrations** — reversible? backward-compatible with the running release?
9. **Performance** — N+1 queries, unbounded lists, broad store subscriptions?
10. **UI states** — loading, empty, error, dark mode, keyboard, long strings?

## 21.6 Definition of done

A change is done when: the code is merged; tests are written and pass; CI is green; docs are
updated where behaviour changed; it works in both themes and is keyboard-operable if user-facing;
errors are handled and legible; nothing is left commented-out or `TODO` without an issue link.

Not done: "works on my machine", "tests come later", "I'll add the empty state after".

## 21.7 Documentation conventions

- These `docs/` files are the design source of truth. Code that contradicts them is a bug in one
  or the other — resolve it, do not let them drift silently.
- Changing an architectural decision means **adding a superseding ADR**, not editing the old one.
- Update the affected doc **in the same PR** as the behaviour change. A docs-update-later PR does
  not exist.
- Inline docstrings explain the *why* of a specific implementation; `docs/` explains the *why* of
  the system. Both are required by the brief; neither substitutes for the other.
- `TODO(phase-N)` marks deferred work, always with the owning phase from
  [19](./19-roadmap.md). A bare `TODO` is a review rejection.
