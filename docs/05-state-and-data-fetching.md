# 05 — State Management & Data Fetching

## 5.1 The dividing line

Two libraries, one rule:

> **TanStack Query owns everything the server knows. Zustand owns everything only the browser
> knows. Neither copies the other's data.**

The failure mode this prevents is the most common bug class in React apps: fetching into a global
store, then having two sources of truth that drift. If a value can be re-fetched, it does not
belong in Zustand.

| Kind of state | Owner | Examples |
|---|---|---|
| Server state | TanStack Query | workflows, executions, credentials, node types, agent runs |
| Client/UI state | Zustand | sidebar collapsed, panel sizes, selected node ids, canvas draft |
| URL state | React Router | current route params, list filters, pagination cursor |
| Session/auth | React Context | current user, tokens, active project |
| Form state | react-hook-form | every form, including node parameter panels |
| Ephemeral state | `useState` | dropdown open, hover, local input focus |

**The single deliberate exception** is the canvas editor draft — see §5.6. It is server data held
in a Zustand store on purpose, and the reasons are written down so nobody "fixes" it later.

## 5.2 Why not just one of them

Zustand alone means hand-rolling caching, deduplication, background refetch, and stale-while-
revalidate — and doing it worse. TanStack Query alone means abusing the cache as a mutable store
for things like "which node is selected," which fights its invalidation model constantly. The
split is not indecision; each tool is doing what it is actually good at.

Redux Toolkit was considered and rejected (ADR-016): with server state removed from the picture,
the remaining client state is small and mostly canvas-shaped, and RTK's boilerplate buys
nothing at that size. Zustand's transient-update and selector story is also materially better for
a 60fps canvas.

## 5.3 `api/` — the transport layer

```ts
// api/client.ts
export const apiClient = axios.create({
  baseURL: env.API_BASE_URL,       // e.g. /api/v1
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});
```

`api/interceptors.ts` attaches, in order:

1. **Request:** `Authorization: Bearer <access>`; `X-Request-Id` (a client-generated correlation
   id, echoed in logs on both sides); active project id header when scoped.
2. **Response (success):** unwrap the envelope if present; pass through otherwise.
3. **Response (error):** normalise into `ApiError`. On 401 with an expired access token, call the
   refresh endpoint **once**, deduplicating concurrent refreshes through a shared promise, then
   replay the original request. On the second 401, clear the session and redirect to `/login`.

Concurrent-refresh deduplication is not optional: without it, a page that fires six queries on
mount will fire six refreshes, and most token rotation schemes will invalidate five of them.

```ts
// api/errors.ts
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,          // stable machine code, e.g. "workflow.not_found"
    message: string,                // human message from server
    readonly details?: unknown,     // field-level validation errors
    readonly requestId?: string,
  ) { super(message); }
}
```

UI branches on `code`, never on the message string. Messages are for humans and will be reworded.

## 5.4 `endpoints/` — the server boundary

Every domain has the same four files. The uniformity is the point: a new engineer can predict the
file layout of a domain they have never opened.

```
endpoints/workflows/
├── keys.ts        # query key factory
├── requests.ts    # raw async fns: URL + params + zod parse. No React.
├── queries.ts     # useQuery / useInfiniteQuery hooks
├── mutations.ts   # useMutation hooks incl. cache invalidation & optimistic updates
└── index.ts       # public surface — pages import only from here
```

### Query keys

Hierarchical factories, so invalidation can be as coarse or as precise as needed:

```ts
export const workflowKeys = {
  all:      ['workflows'] as const,
  lists:    () => [...workflowKeys.all, 'list'] as const,
  list:     (f: WorkflowFilters) => [...workflowKeys.lists(), f] as const,
  details:  () => [...workflowKeys.all, 'detail'] as const,
  detail:   (id: string) => [...workflowKeys.details(), id] as const,
  versions: (id: string) => [...workflowKeys.detail(id), 'versions'] as const,
};
```

`invalidateQueries({ queryKey: workflowKeys.lists() })` refreshes every list regardless of filter,
without touching detail caches. Ad-hoc inline key arrays are banned by review.

### Requests

```ts
export async function fetchWorkflow(id: string): Promise<Workflow> {
  const { data } = await apiClient.get(`/workflows/${id}`);
  return workflowSchema.parse(data);      // the validation boundary from 04 §4.7
}
```

### Queries

```ts
export function useWorkflow(id: string) {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => fetchWorkflow(id),
    staleTime: 30_000,
  });
}
```

### Mutations

```ts
export function useUpdateWorkflow(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: WorkflowUpdate) => updateWorkflow(id, input),
    onSuccess: (updated) => {
      qc.setQueryData(workflowKeys.detail(id), updated);   // write-through
      qc.invalidateQueries({ queryKey: workflowKeys.lists() });
    },
  });
}
```

**Rule:** a mutation is responsible for its own invalidation. A component MUST NOT call
`invalidateQueries` — if it needs to, the mutation hook is incomplete.

## 5.5 QueryClient defaults

```ts
// lib/query-client.ts
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (count, err) =>
        isApiError(err) && err.status >= 400 && err.status < 500 ? false : count < 2,
      refetchOnWindowFocus: false,
      throwOnError: false,
    },
    mutations: { retry: 0 },
  },
});
```

Reasoning worth keeping: **never retry 4xx** (the request is wrong; retrying is pure latency),
**never retry mutations** (side effects may have landed), and **`refetchOnWindowFocus: false`**
because an editor that silently refetches when you alt-tab back is disorienting. Live-ness for
running executions comes from SSE, which is precise, rather than from polling everything.

### Per-resource cache policy

| Resource | staleTime | Notes |
|---|---|---|
| Node type registry | `Infinity` | Static per deploy. Fetched once at boot, hydrated into the canvas. |
| Workflow list | 30 s | |
| Workflow detail | 30 s | Editor takes a snapshot into the canvas store; see §5.6 |
| Executions list | 5 s | Short — this is the monitoring surface |
| Execution detail (terminal) | `Infinity` | An execution that finished can never change |
| Execution detail (running) | 0 + SSE | Events patch the cache directly |
| Credentials | 60 s | Never contains secret values |
| Current user | 5 min | |

The terminal-execution rule is a genuinely large win: execution detail pages are heavy and
immutable, so caching them forever is both correct and fast.

## 5.6 The canvas store — the deliberate exception

The workflow editor holds a **draft** of the graph: nodes, edges, and parameters mutated dozens of
times per second by dragging, typed into by the parameter panel, and undoable. This is server data
living in a Zustand store, which §5.1 otherwise forbids. It is justified because:

1. A React Query cache entry is not a legal mutation target at 60fps.
2. Undo/redo needs an explicit, ordered history that a cache does not model.
3. The draft is *divergent by design* — it differs from the server until saved, and the UI must
   show that difference ("unsaved changes").

**The lifecycle that keeps it honest:**

```
useWorkflow(id) ──loads──▶ canvasStore.hydrate(workflow)   // once, on mount / id change
      canvas edits ──────▶ canvasStore (isDirty = true)
      save ──────────────▶ useUpdateWorkflow → server → canvasStore.markSaved(version)
      unmount ───────────▶ canvasStore.reset()
```

**Rules:** hydration happens exactly once per workflow id; the store is reset on unmount; the
query cache is never written from the store except through the save mutation's `onSuccess`. If the
server version changes underneath (someone else saved), the save returns 409 and the UI offers
reload-or-overwrite rather than silently clobbering.

### Store shape

```ts
interface CanvasState {
  workflowId: string | null;
  nodes: FlowNode[];
  edges: FlowEdge[];
  isDirty: boolean;
  savedVersionId: string | null;
  past: GraphSnapshot[];      // undo
  future: GraphSnapshot[];    // redo

  hydrate(w: Workflow): void;
  reset(): void;
  addNode(type: string, position: XYPosition): string;
  updateNodeParams(id: string, params: Record<string, unknown>): void;
  removeNodes(ids: string[]): void;
  connect(c: Connection): void;
  undo(): void;
  redo(): void;
  markSaved(versionId: string): void;
}
```

**Slicing for performance.** Selection lives in a *separate* store (`selection-store.ts`). Node
components subscribe to `selection` but not to `nodes`; the inspector subscribes to one node's
params, not the array. Mixing selection into the graph store would re-render every node on every
click — the single biggest canvas performance mistake available.

Undo history stores **snapshots capped at 50 entries**, not diffs. Graphs are small (tens of KB),
snapshots are trivially correct, and diff-based undo is a bug farm. History is *not* persisted.

## 5.7 Other stores

```ts
// store/ui-store.ts — persisted to localStorage via zustand/middleware persist
{ sidebarCollapsed, inspectorWidth, bottomPanelHeight, activeInspectorTab, theme }

// store/selection-store.ts — ephemeral
{ selectedNodeIds: string[], hoveredNodeId: string | null, ... }
```

`ui-store` uses `persist` with an explicit `version` and a `migrate` function from day one — a
persisted store without a migration path breaks for every existing user the first time its shape
changes.

## 5.8 Real-time integration

SSE events patch the React Query cache directly. The subscription lives in one hook, so there is
exactly one place where push and pull meet:

```ts
export function useExecutionStream(executionId: string, enabled: boolean) {
  const qc = useQueryClient();
  useEventSource(`/executions/${executionId}/stream`, enabled, (event) => {
    switch (event.type) {
      case 'node.started':
      case 'node.finished':
        qc.setQueryData(executionKeys.detail(executionId), patchNodeRun(event));
        break;
      case 'execution.finished':
        qc.invalidateQueries({ queryKey: executionKeys.detail(executionId) });
        qc.invalidateQueries({ queryKey: executionKeys.lists() });
        break;
    }
  });
}
```

`useEventSource` (in `hooks/`) owns reconnection with exponential backoff and `Last-Event-ID`
resume, and closes the connection on unmount and on `execution.finished`. Leaving SSE connections
open is how you exhaust the browser's six-connections-per-host budget and wedge the whole app.

## 5.9 Optimistic updates

Used **only** where the operation is near-certain and the visual feedback matters: renaming,
toggling a workflow active, favouriting, reordering. Everything else — anything that creates,
deletes, or executes — waits for the server, with a pending state on the button.

Optimism is a UX tool, not a default. An optimistic delete that rolls back after 800 ms is worse
than a spinner, because the user has already moved on believing it worked.

Standard pattern: `onMutate` cancels in-flight queries, snapshots previous data, writes the
optimistic value; `onError` restores the snapshot; `onSettled` invalidates.

## 5.10 Anti-patterns, explicitly banned

1. `useEffect` that copies query data into a Zustand store. (The one exception is §5.6's
   single hydrate call, which is not an effect-driven mirror but a one-shot handoff.)
2. Storing an access token in a Zustand store. Auth lives in `AuthProvider`.
3. Calling `apiClient` from a component.
4. `queryKey: ['workflows', id]` inline. Use the factory.
5. A `loading` boolean in a store alongside a query's own `isPending`.
6. `refetchInterval` on anything that has an SSE channel.
7. Subscribing to a whole store: `useCanvasStore()` with no selector. Always select.
