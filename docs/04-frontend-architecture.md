# 04 — Frontend Architecture

## 4.1 The folder contract

The brief fixes the top-level folders. This section makes each one's meaning unambiguous, because
a folder set without a rule for what goes where degrades into ten synonyms for "misc".

```
neuroflow-frontend/src/
├── api/          # HTTP transport. axios instance, interceptors, error normalisation.
├── components/   # Presentational + composite UI. No data fetching. No business rules.
├── config/       # Build-time & env-derived constants. Zero imports from elsewhere in src/.
├── context/      # React context providers only (theme, auth session, app shell).
├── endpoints/    # THE SERVER BOUNDARY. Request fns + TanStack Query hooks, per domain.
├── hooks/        # Reusable non-domain React hooks (useDebounce, useHotkey, useMobile).
├── lib/          # Third-party adapters & app-wide singletons (queryClient, cn, monaco setup).
├── pages/        # Route-level screens. Compose components + endpoint hooks. Thin.
├── routing/      # Route table, guards, lazy boundaries, path constants.
├── store/        # Zustand stores (client state). [added — see 4.2]
├── types/        # Shared TypeScript types + zod schemas mirroring API contracts.
└── utils/        # Pure functions. No React, no network, no state. Unit-testable in isolation.
```

### The one-line test for each folder

| Folder | Question that decides membership |
|---|---|
| `api/` | "Is this about *how* we speak HTTP?" (headers, retries, error shape) |
| `endpoints/` | "Is this about *what* we ask the server for?" (URLs, query keys, cache policy) |
| `utils/` | "Could this run in Node with no React and no fetch?" |
| `lib/` | "Is this configuring or wrapping a third-party library?" |
| `hooks/` | "Is this a React hook with no knowledge of our domain?" |
| `components/` | "Would this render identically given props, in Storybook, with no server?" |
| `pages/` | "Does a URL point at this?" |
| `store/` | "Is this state the server does not own?" |

`api/` vs `endpoints/` is the distinction people get wrong most often. `api/` is written once and
rarely touched. `endpoints/` grows with every feature.

## 4.2 Deviation from the brief: `store/`

⚠️ The brief lists `context/` but no state folder. Putting Zustand stores in `context/` is wrong —
Zustand's entire point is that it does *not* use context, and mixing them guarantees confusion
about which mechanism owns what.

**Decision:** add `src/store/`. `context/` keeps only genuine React providers: `ThemeProvider`,
`AuthProvider`, `AppShellProvider`, plus React Flow's own `ReactFlowProvider`. Rationale in
ADR-017. This is the only structural addition to the brief's layout, and it is additive.

## 4.3 Feature-first organisation inside the folders

Folders are horizontal (by kind); features are vertical (by domain). Both matter, so **the
domain name is the second level inside every folder**:

```
src/endpoints/workflows/       src/components/workflows/      src/types/workflows.ts
src/endpoints/executions/      src/components/executions/     src/types/executions.ts
src/endpoints/agents/          src/components/agents/         src/types/agents.ts
src/endpoints/credentials/     src/components/credentials/    src/types/credentials.ts
src/endpoints/nodes/           src/components/canvas/         src/types/nodes.ts
src/endpoints/auth/            src/components/common/         src/types/api.ts
```

Deleting a feature should mean deleting one folder per top-level directory and nothing else. If
removing "credentials" requires editing fifteen unrelated files, the boundary has leaked.

**Fixed domains for v1:** `auth`, `workflows`, `executions`, `nodes`, `agents`, `credentials`,
`projects`, `settings`. Adding a ninth requires a line in this document.

## 4.4 Full tree (target state, end of Phase 3)

```
src/
├── api/
│   ├── client.ts               # axios instance, baseURL from config
│   ├── interceptors.ts         # auth header, 401 -> refresh -> retry once, request-id
│   ├── errors.ts               # ApiError class, isApiError, toUserMessage()
│   └── index.ts
├── components/
│   ├── ui/                     # shadcn primitives — DO NOT hand-edit; regenerate via CLI
│   ├── common/                 # PageHeader, EmptyState, ErrorBoundary, ConfirmDialog,
│   │                           # DataTable, CopyButton, RelativeTime, StatusBadge
│   ├── layout/                 # AppShell, Sidebar, Topbar, Breadcrumbs, CommandPalette
│   ├── canvas/                 # FlowCanvas, nodes/, edges/, handles/, controls/, minimap/
│   ├── inspector/              # NodeInspector, ParameterForm, fields/, DataPanel, JsonViewer
│   ├── workflows/              # WorkflowCard, WorkflowList, VersionHistory, RunButton
│   ├── executions/             # ExecutionTable, ExecutionDetail, NodeRunTimeline, LogStream
│   ├── agents/                 # AgentCanvas, ToolPicker, PromptEditor, ChatTester, TraceView
│   └── credentials/            # CredentialForm, CredentialPicker, OAuthConnectButton
├── config/
│   ├── env.ts                  # zod-parsed import.meta.env — fails loudly at boot
│   ├── constants.ts            # timeouts, page sizes, canvas limits, poll intervals
│   └── features.ts             # feature flags
├── context/
│   ├── ThemeProvider.tsx
│   ├── AuthProvider.tsx        # session object + login/logout; tokens live here, not in stores
│   └── AppProviders.tsx        # single composed provider tree used by main.tsx
├── endpoints/
│   └── <domain>/{keys.ts, requests.ts, queries.ts, mutations.ts, index.ts}
├── hooks/
│   ├── use-mobile.ts           # exists
│   ├── use-debounce.ts  use-hotkeys.ts  use-clipboard.ts
│   ├── use-event-source.ts     # SSE subscription with reconnect
│   └── use-local-storage.ts
├── lib/
│   ├── utils.ts                # cn (exists)
│   ├── query-client.ts         # QueryClient singleton + default options
│   ├── monaco.ts               # editor themes, expression language registration
│   ├── layout.ts               # elkjs auto-layout wrapper
│   └── date.ts                 # date-fns wrappers, single formatting vocabulary
├── pages/
│   ├── auth/{LoginPage,SignupPage,ForgotPasswordPage}.tsx
│   ├── workflows/{WorkflowListPage,WorkflowEditorPage}.tsx
│   ├── agents/{AgentListPage,AgentBuilderPage}.tsx
│   ├── executions/{ExecutionListPage,ExecutionDetailPage}.tsx
│   ├── credentials/CredentialListPage.tsx
│   ├── settings/{ProfilePage,MembersPage,ApiKeysPage}.tsx
│   └── NotFoundPage.tsx
├── routing/
│   ├── paths.ts                # every URL as a typed builder — no string literals in components
│   ├── routes.tsx              # route objects + lazy()
│   ├── guards.tsx              # RequireAuth, RequireRole
│   └── index.ts
├── store/
│   ├── canvas-store.ts         # the editor graph draft (the big one)
│   ├── ui-store.ts             # sidebar collapsed, panel sizes, active tab
│   └── selection-store.ts      # canvas selection (split for render performance)
├── types/
│   ├── api.ts                  # Paginated<T>, ApiErrorBody, Timestamps
│   ├── workflows.ts  executions.ts  nodes.ts  agents.ts  credentials.ts  auth.ts
│   └── index.ts
├── utils/
│   ├── graph.ts                # topo sort, cycle detect, reachability, descendants
│   ├── expression.ts           # {{ }} detection, highlight ranges, path extraction
│   ├── json.ts                 # safe stringify, deep get/set, size estimate
│   ├── format.ts               # bytes, duration, number, truncate
│   └── validation.ts           # shared zod refinements
├── App.tsx
└── main.tsx
```

## 4.5 Layering rules

```
pages → components → ui
  ↓         ↓
endpoints → api
  ↓
types ← utils ← config
```

**MUST:**
1. Components MUST NOT import from `api/`. They use `endpoints/` hooks or receive props.
2. `utils/` MUST NOT import React, `endpoints/`, `store/`, or `components/`. Pure functions only.
3. `config/` MUST NOT import anything from `src/`. It is a leaf.
4. `types/` MUST NOT import runtime values other than zod.
5. Business logic MUST NOT live in components. A component decides *what to render*; a hook,
   util, or store decides *what is true*. The brief calls this out explicitly and it is the rule
   most likely to erode under deadline pressure.
6. Cross-domain imports between `components/<a>/` and `components/<b>/` are forbidden. Shared
   pieces move to `components/common/`.

**Enforcement.** These are not honour-system rules — add `eslint-plugin-boundaries` (or
`import/no-restricted-paths`) in Phase 1 and fail CI on violation. A layering rule that is not
mechanically checked is a comment.

## 4.6 Routing

`react-router` v7 in declarative mode. Routes are data, defined once in `routing/routes.tsx`.

```
/login  /signup  /forgot-password              public
/                                              -> redirect /workflows
/workflows                                     list
/workflows/:workflowId                         editor (canvas)
/workflows/:workflowId/executions/:executionId  editor in read-only run-inspection mode
/agents                                        list
/agents/:agentId                               agent builder
/executions                                    global executions list
/executions/:executionId                       execution detail
/credentials                                   list + create sheet
/settings/profile  /settings/members  /settings/api-keys  /settings/variables
/*                                             404
```

**Rules.**
- Every path is produced by a builder in `routing/paths.ts`: `paths.workflowEditor(id)`. No
  route string literal may appear in a component — this is what makes a URL change a one-file change.
- Page components are `lazy()`-loaded. The editor route additionally prefetches `@xyflow/react`
  and Monaco on hover of any workflow card.
- Guards are components (`<RequireAuth>`), not loader side effects, so they are testable in
  isolation and render a real skeleton while the session resolves.
- **URL is state.** Executions list filters (`?status=error&workflowId=…&cursor=…`) live in the
  query string, not in a store, so a filtered view is shareable. This is a deliberate constraint
  on [05](./05-state-and-data-fetching.md).

## 4.7 Type strategy

The frontend and backend are separate deployables, so types are contracts, not shared code.

1. **zod schemas are the single source of truth** on the client. `types/workflows.ts` exports both
   the schema and `z.infer` type.
2. **Validate at the boundary, once.** Response bodies are parsed in `endpoints/*/requests.ts`.
   Past that line, data is trusted and typed. This turns a backend contract change into a loud,
   located error instead of `undefined is not an object` three components deep.
3. **`import type` everywhere.** `verbatimModuleSyntax` is on; a value import of a type is a build
   error. Configure the ESLint `consistent-type-imports` autofix so this is never manual.
4. **No enums.** `erasableSyntaxOnly` bans them. Use:
   ```ts
   export const EXECUTION_STATUS = ['queued','running','success','error','waiting','canceled'] as const;
   export type ExecutionStatus = (typeof EXECUTION_STATUS)[number];
   ```
   This is also better: the array is iterable for filter UIs, which an enum is not.
5. `any` is banned by lint. `unknown` plus a zod parse is the escape hatch.

⚠️ Generating types from the backend's OpenAPI schema is tempting and **rejected for v1**
(ADR-018): generated types are structurally correct but semantically weak (every optional field
becomes `| undefined`), they cannot express the runtime validation we want, and the generator
becomes a build-order dependency between two repos' CI. Revisit if drift becomes a real incident
rather than a hypothetical.

## 4.8 Error handling

Three tiers, each with an owner:

1. **Transport errors** — `api/interceptors.ts` normalises every failure into `ApiError`
   (`status`, `code`, `message`, `details`, `requestId`). A 401 triggers exactly one refresh-and-retry;
   a second 401 logs out.
2. **Query errors** — rendered inline by the component that owns the query (an `EmptyState` with
   a retry). Never a toast for a failed read: toasts for reads are noise the user cannot act on.
3. **Mutation errors** — a toast with the server's message plus the `requestId` in a copyable
   detail line, because that ID is what makes a support ticket diagnosable.

An `ErrorBoundary` wraps each route element and the canvas separately, so a crash in the canvas
does not blank the whole shell.

## 4.9 Performance rules

The canvas makes this a genuinely performance-sensitive app, which most CRUD frontends are not.

- **Selector-scoped subscriptions.** Zustand components subscribe to the narrowest slice possible.
  Subscribing a node component to the whole graph re-renders 150 nodes on every drag frame.
- **`React.memo` on every custom node component**, with an explicit comparator on
  `data.paramsHash` rather than deep equality.
- **Never store transient drag state in React.** Position updates during a drag are handled by
  React Flow internally and committed to the store on drag *end*.
- Route-level code splitting; Monaco and `elkjs` are dynamically imported on first use only.
- Virtualise any list over 100 rows (executions, node picker).
- Budget: interaction p95 < 100 ms at 150 nodes, enforced by a Playwright performance test in CI
  ([17](./17-testing-strategy.md)).

## 4.10 Composition of `main.tsx`

The provider order is load-bearing and should not be shuffled casually:

```tsx
<StrictMode>
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>   {/* outermost: auth needs to fetch */}
      <ThemeProvider>
        <AuthProvider>                            {/* needs queries; guards need it */}
          <TooltipProvider>
            <RouterProvider router={router} />
            <Toaster />
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </ErrorBoundary>
</StrictMode>
```

`ReactFlowProvider` is deliberately **not** here — it wraps only the editor page, so canvas
context does not exist on routes that have no canvas.
