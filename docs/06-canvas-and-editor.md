# 06 — Canvas & Editor Design

The canvas is the product. Everything else is CRUD around it. This document specifies its
structure, its interaction model, and the performance constraints that shape both.

## 6.1 Library choice

**`@xyflow/react` v12 (React Flow).** (ADR-012)

It provides pan/zoom, node/edge rendering, connection dragging, selection, minimap, and viewport
maths — roughly six weeks of work that is entirely undifferentiated. It is unopinionated about
node internals, which is where all our differentiation lives.

Rejected: hand-rolled SVG/canvas (months of work to reach parity, and the accessibility story is
grim); `reactflow` v11 (superseded); Konva/PixiJS (no DOM nodes means re-implementing forms,
focus, and text selection inside a canvas — a bad trade for a form-heavy product).

⚠️ **Risk:** React Flow under React 19 `StrictMode` is the stack's least-proven combination.
Phase 1 opens with a spike: 200 nodes, 300 edges, drag, connect, undo, `StrictMode` on. If it
fails, the fallback is pinning React 18 for the frontend, which is cheap *now* and expensive
after twenty components exist.

## 6.2 Editor layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Topbar: ← name ✎ · status · [Test workflow] [Save] · ⋯ · Active ⏻        │  56px
├───────┬──────────────────────────────────────────────┬───────────────────┤
│       │                                              │                   │
│ Node  │              CANVAS                          │   INSPECTOR       │
│ Panel │   (React Flow: pan/zoom/select/connect)      │   (selected node) │
│ 280px │                                              │   380–640px       │
│ (drawer)                                             │   resizable       │
│       │   ┌──────────┐ Controls  ┌────────┐          │  ┌─────────────┐  │
│       │   │ minimap  │ ⊕ ⊖ ⤢ ⌗   │ +  Add │          │  │ INPUT│PARAMS│ │
│       │   └──────────┘           └────────┘          │  │      │OUTPUT│ │
├───────┴──────────────────────────────────────────────┴──┴─────────────┴──┤
│ Bottom panel (collapsible): Executions | Logs | Data          180–400px  │
└──────────────────────────────────────────────────────────────────────────┘
```

Built with `react-resizable-panels` (already installed). Panel sizes persist to `ui-store`.
The node panel is a drawer, not a fixed column: at rest the canvas gets the full width, because
the canvas is what the user is thinking about.

**Inspector layout is the n8n three-column idea and it is worth copying exactly:** input data on
the left, parameters in the middle, output data on the right. Seeing what went in, what you are
configuring, and what came out simultaneously is the single biggest debugging affordance in the
category. On narrow viewports it degrades to tabs rather than stacking.

## 6.3 Component structure

```
components/canvas/
├── FlowCanvas.tsx              # <ReactFlow> host: handlers, viewport, keybindings
├── nodes/
│   ├── BaseNode.tsx            # shared chrome: card, icon, title, status ring, handles
│   ├── TriggerNode.tsx         # rounded-left "lightning" shape, output handle only
│   ├── ActionNode.tsx          # the default rectangle
│   ├── BranchNode.tsx          # IF/Switch: multiple labelled outputs
│   ├── MergeNode.tsx           # multiple labelled inputs
│   ├── AgentNode.tsx           # taller; sub-handles for model/tools/memory (see 14)
│   ├── StickyNote.tsx          # not executed; documentation on the canvas
│   └── index.ts                # nodeTypes map passed to ReactFlow
├── edges/
│   ├── FlowEdge.tsx            # smoothstep + hover affordances (+ button, delete)
│   └── index.ts
├── handles/{InputHandle,OutputHandle,HandleLabel}.tsx
├── controls/{CanvasControls,ZoomIndicator,TidyUpButton,MiniMapPanel}.tsx
├── overlay/{ConnectionHint,DropIndicator,SelectionToolbar}.tsx
└── NodePicker.tsx              # cmdk-powered search palette
```

`nodeTypes` and `edgeTypes` MUST be defined **at module scope**, never inline in the render — an
inline object is a new reference every render and remounts every node on the canvas. This is the
number-one React Flow performance bug and it is worth a lint rule.

## 6.4 Node visual anatomy

```
        ┌─────────────────────────────────┐
   ●────┤ ┌────┐                      ⚠️  │────●  output handle
 input  │ │icon│  HTTP Request           │
 handle │ └────┘  GET api.stripe.com     │
        │ ─────────────────────────────── │
        │ ✓ 1.2s · 24 items               │  ← run summary strip (post-execution only)
        └─────────────────────────────────┘
              ▲ 3px status ring
```

- **Size:** 240 × 76 px default, snapped to a 16 px grid. Fixed width is what makes a graph of 60
  nodes readable — variable-width nodes destroy the visual rhythm.
- **Icon:** 32 px, in a rounded tile tinted by the node's category colour. The icon is the primary
  identification cue at low zoom, so it must be legible at 40% scale.
- **Title:** the user-set node name, `font-medium`, truncated with a tooltip. **Subtitle:** a
  descriptor-supplied summary of the current parameters (`GET api.stripe.com`) — this is what
  turns a graph from "six HTTP nodes" into something readable, and it is why the node descriptor
  spec in [13](./13-node-catalog-and-sdk.md) includes a `subtitle` expression.
- **Status ring:** the left border, 3 px — idle (border), running (animated primary), success
  (success), error (destructive), waiting (warning), disabled (muted + 60% node opacity).
- **Run summary strip:** appears only after an execution, showing duration and item count. Click
  opens the data panel for that node.
- **Badges:** pinned-data pin, notes indicator, retry-configured, error-branch-configured.

**At zoom < 50%** nodes render a simplified variant — icon and title only, no subtitle, no strip.
React Flow exposes zoom via `useStore`; subscribing to a *bucketed* zoom level (not the raw float)
avoids re-rendering every node on every wheel tick.

## 6.5 Edges

- **Type:** `smoothstep` with 8 px border radius. Bezier curves look fluid with two nodes and
  become spaghetti with twenty; orthogonal routing reads as structure.
- **Idle:** 2 px, `--border`. **Hover:** 3 px, `--primary`, endpoints revealed. **Selected:**
  3 px primary with a subtle glow. **Running:** animated dash flowing source→target — the single
  most effective "the system is alive" cue in the whole UI.
- **Hover affordances:** a `+` button at the midpoint inserts a node *into* the connection
  (splice: rewire A→new→B in one action), and a `×` deletes it. Insert-on-edge is the highest-value
  editing gesture in n8n and it must ship in v1.
- **Labels:** branch outputs carry pill labels (`true` / `false` / case name) anchored at the
  source handle, not the midpoint, so they stay readable when edges are long.
- **Error edges** are dashed and use `--destructive`, so a failure path is visually distinct from
  the happy path without being read.

## 6.6 Interaction model

| Gesture | Result |
|---|---|
| Drag empty canvas | Pan |
| Scroll / pinch | Zoom to cursor |
| Space + drag | Pan (even over a node) |
| Click node | Select |
| Double-click node | Open inspector |
| Drag from output handle | Start connection; compatible inputs highlight, others dim |
| Drop connection on empty canvas | Open node picker, auto-connect on choose |
| Drag node onto an edge | Splice into that connection |
| `Tab` | Open node picker at viewport centre |
| `Delete` / `Backspace` | Delete selection |
| `Ctrl/Cmd+C/V/D` | Copy / paste / duplicate (paste offsets by 24 px) |
| `Ctrl/Cmd+Z` / `Shift+Z` | Undo / redo |
| `Ctrl/Cmd+A` | Select all |
| `Ctrl/Cmd+S` | Save |
| `Ctrl/Cmd+Enter` | Execute workflow |
| `Ctrl/Cmd+K` | Command palette |
| `Shift+drag` | Rubber-band select |
| `F` | Fit view to selection, or all if none |
| `Ctrl/Cmd+Shift+L` | Tidy up (auto-layout) |
| Right-click node/edge/canvas | Context menu |

**Connection validation** runs in `isValidConnection`: no self-loops; no duplicate edges; no
cycles unless the target is an explicit loop node; handle types must be compatible (a `main`
output cannot enter a `tool` input). Invalid targets dim to 30% during a connection drag, so the
rule is discovered by trying rather than by reading an error.

## 6.7 Adding nodes — the node picker

`cmdk` (already installed) powers a search palette that is the primary way nodes get added.

- Opens via `Tab`, the `+` button, an edge `+`, or dropping a connection on empty canvas.
- Fuzzy search across name, category, aliases, and description. Aliases matter more than they
  sound: a user typing "gpt" must find "OpenAI Chat Model", and "http"/"api"/"rest"/"curl" must
  all find HTTP Request.
- Grouped by category with recently-used pinned at top; keyboard-first with arrow navigation.
- Shows the node icon, name, and one-line description; `Enter` inserts at the target position and
  auto-connects if invoked from a handle or edge.
- **Drag-and-drop from the node panel** remains supported (it is the discoverable path for new
  users) via HTML5 drag with a `DropIndicator` overlay, but search is the path power users live in.

## 6.8 Auto-layout

`elkjs`, layered algorithm, left-to-right, dynamically imported on first use.

```ts
{ 'elk.algorithm': 'layered',
  'elk.direction': 'RIGHT',
  'elk.spacing.nodeNode': '64',
  'elk.layered.spacing.nodeNodeBetweenLayers': '120',
  'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP' }
```

Applied to the whole graph, or to the selection only if a multi-selection exists. The transition
is animated over 300 ms — an instant jump makes users lose track of which node was which — and it
is a single undoable action.

## 6.9 The inspector

Rendered generically from the node's `NodeTypeDescriptor.properties` ([13](./13-node-catalog-and-sdk.md)).
**No node ships bespoke inspector code.** This is the constraint that makes the node catalog
cheap to grow, and it must be defended: the moment one node gets a hand-written panel, twenty will.

**Field kinds:** `string`, `number`, `boolean`, `options` (select), `multiOptions`, `json`,
`code` (Monaco), `credential` (picker + inline create), `collection` (repeatable group),
`resourceLocator` (by id / by URL / from list), `dateTime`, `color`, `hidden`, `notice`.

Rendered with `react-hook-form` + a zod resolver derived from the descriptor. Conditional
visibility comes from each property's `displayOptions.show/hide` predicate evaluated against the
current parameter values — this is how a node shows "Body" only when Method is POST.

### Expression editing

Any field can be switched from a fixed value to an expression via a small `fx` toggle.

- Syntax `{{ $json.field }}`, with `$json`, `$node["Name"].json`, `$items()`, `$now`, `$env`,
  `$workflow`, `$execution`, `$vars` in scope ([12](./12-execution-engine.md) §12.6).
- Monaco with a custom language: highlighting inside `{{ }}`, autocomplete driven by the *actual
  input data* of the selected node, and a live-evaluated result preview underneath the field.
- **Drag a field from the input data panel onto a parameter** to insert the correct expression.
  This is how non-programmers write expressions successfully, and it is worth the implementation
  cost.

## 6.10 Data panels

The left (input) and right (output) panels of the inspector, and the bottom panel, share one
`DataView` component with four modes:

- **Table** — items as rows, JSON keys as columns; the default, because it makes "24 items" concrete.
- **JSON** — collapsible tree with copy-path on hover; `$json.user.email` is copyable directly
  into an expression.
- **Schema** — inferred key/type tree; the surface you drag from.
- **Binary** — file list with previews for image/PDF/text.

Item pagination at 20 per page, virtualised. Large payloads (>1 MB) render a truncation notice
with a download link rather than attempting to render.

### Pinned data

A node's output can be **pinned**: frozen sample data used on every subsequent manual run instead
of calling the real service. This lets a user iterate on the nodes downstream of a slow or
rate-limited API without hammering it, and it is the closest thing to a debugger the v1 scope
includes. Pinned data is stored on the workflow version, is visibly badged on the node, and is
**ignored in production executions** — a pin that silently faked production data would be a
serious correctness bug.

## 6.11 Execution feedback on the canvas

During a run, the canvas is the progress UI:

1. Node status rings update live from SSE.
2. The active node's edge animates.
3. Each completed node shows its run summary strip with item count and duration.
4. On failure, the failing node gets a destructive ring and an error badge; clicking it opens the
   inspector on the error, with the stack/response body.
5. The bottom panel streams log lines with node-scoped filtering.

**Run inspection mode** (`/workflows/:id/executions/:execId`) reuses the same canvas in read-only
form, hydrated from a past execution's data. Same component, `readOnly` flag — not a second
implementation.

## 6.12 Performance rules

Non-negotiable given a 150-node target at 60fps:

1. `nodeTypes` / `edgeTypes` at module scope.
2. Every node component wrapped in `React.memo` with a comparator over `id`, `selected`,
   `data.paramsHash`, `data.status`.
3. Node components subscribe to selection and status via narrow Zustand selectors; they never
   read the `nodes` array.
4. Position changes commit to the store on drag **end**; during a drag React Flow owns position.
5. `onlyRenderVisibleElements` enabled above 80 nodes.
6. Expression previews debounced 300 ms; each preview is a network call.
7. Minimap disabled above 250 nodes (it re-renders on every viewport change).
8. `elkjs` and Monaco dynamically imported.
9. A soft warning at 200 nodes suggesting sub-workflow extraction — a graph that large is also a
   comprehension problem, not just a rendering one.

## 6.13 Accessibility

A node canvas is inherently hard to make accessible; the goal is that nothing *except* spatial
arrangement requires a mouse.

- Full keyboard node navigation: `Tab` cycles nodes in topological order, arrows move selection
  along edges, `Enter` opens the inspector.
- Nodes are focusable with `role="button"` and an `aria-label` of name, type, and status.
- Live region announces execution status changes.
- Status is never colour-only: icons and text accompany every state.
- Everything in the inspector, the node picker, and all panels is fully keyboard-operable and
  screen-reader labelled — these are ordinary DOM and have no excuse.
- `prefers-reduced-motion` disables edge dash animation and layout transitions.
