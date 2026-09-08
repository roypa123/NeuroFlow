import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type Viewport,
} from '@xyflow/react'
import { create } from 'zustand'
import type { NodeTypeDescriptor } from '@/types/node-types'
import type { WorkflowGraph } from '@/types/workflows'

// Per-workflow-session canvas state -- NOT persisted (docs/05-state-and-
// data-fetching.md #5.1: client-only state, but this one is scoped to
// "currently open editor tab", not durable across reloads like ui-store/
// workspace-store). Undo/redo history lives here too, per
// docs/06-canvas-and-editor.md #6.6.
//
// A node's React Flow `type` is a small, fixed render-kind ("trigger" |
// "branch" | "action") resolved once from its descriptor -- never the
// raw node-type key (e.g. "neuroflow.if"). That key lives in
// `data.nodeTypeKey`. This is what lets `nodeTypes` stay a module-scope
// constant (docs/06-canvas-and-editor.md #6.12 rule 1) instead of being
// rebuilt from the fetched catalog.
//
// Deliberately never "default"/"input"/"output"/"group" -- those are
// @xyflow/react's own built-in type names, and its base stylesheet ships a
// `.react-flow__node-default { width: 150px; padding: 10px; ... }` rule
// that collides with our custom node's own sizing the moment a node is
// registered under that key, even with a full component override.

export type RenderKind = 'trigger' | 'branch' | 'action'

export function renderKindFor(descriptor: NodeTypeDescriptor | undefined): RenderKind {
  if (!descriptor) return 'action'
  if (descriptor.group === 'trigger') return 'trigger'
  if (descriptor.outputs.length > 1) return 'branch'
  return 'action'
}

export interface NodeData extends Record<string, unknown> {
  nodeTypeKey: string
  typeVersion: number
  label: string | null
  parameters: Record<string, unknown>
  status: 'idle' | 'running' | 'success' | 'error' | 'waiting' | 'disabled'
  // No inspector UI yet (docs/12-execution-engine.md #12.4's onError/retry
  // config is a later polish item) -- carried through load/save so a
  // graph that already has non-default values round-trips exactly rather
  // than silently resetting them, per the Phase 3 exit criterion.
  onError: 'stop' | 'continue' | 'continueErrorOutput'
  maxTries: number
  waitBetweenTriesMs: number
}

export type FlowNode = Node<NodeData>
export type FlowEdge = Edge

interface Snapshot {
  nodes: FlowNode[]
  edges: FlowEdge[]
}

interface CanvasState {
  workflowId: string | null
  baseVersionId: string | null
  nodes: FlowNode[]
  edges: FlowEdge[]
  viewport: Viewport
  isDirty: boolean
  selectedNodeId: string | null
  history: { past: Snapshot[]; future: Snapshot[] }

  loadGraph: (
    workflowId: string,
    baseVersionId: string | null,
    graph: WorkflowGraph,
    descriptorsByKey: Record<string, NodeTypeDescriptor>,
  ) => void
  markSaved: (baseVersionId: string) => void
  toGraph: () => WorkflowGraph

  onNodesChange: (changes: NodeChange<FlowNode>[]) => void
  onEdgesChange: (changes: EdgeChange<FlowEdge>[]) => void
  onConnect: (connection: Connection) => void
  setViewport: (viewport: Viewport) => void

  addNode: (
    descriptor: NodeTypeDescriptor,
    position: { x: number; y: number },
    connectFrom?: { nodeId: string; handle: string | null },
  ) => string
  removeNode: (nodeId: string) => void
  updateNodeParameters: (nodeId: string, parameters: Record<string, unknown>) => void
  updateNodeLabel: (nodeId: string, label: string | null) => void
  setSelectedNodeId: (id: string | null) => void
  applyAutoLayout: (positions: Record<string, { x: number; y: number }>) => void

  undo: () => void
  redo: () => void
  canUndo: () => boolean
  canRedo: () => boolean
}

const MAX_HISTORY = 50

function snapshot(state: CanvasState): Snapshot {
  return { nodes: state.nodes, edges: state.edges }
}

function defaultParameters(descriptor: NodeTypeDescriptor): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  for (const prop of descriptor.properties) {
    if (prop.default !== null && prop.default !== undefined) {
      params[prop.name] = prop.default
    }
  }
  return params
}

let nodeCounter = 0
function nextNodeId(): string {
  nodeCounter += 1
  return `n_${Date.now().toString(36)}_${nodeCounter}`
}

export const useCanvasStore = create<CanvasState>()((set, get) => ({
  workflowId: null,
  baseVersionId: null,
  nodes: [],
  edges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  isDirty: false,
  selectedNodeId: null,
  history: { past: [], future: [] },

  loadGraph: (workflowId, baseVersionId, graph, descriptorsByKey) => {
    const nodes: FlowNode[] = graph.nodes.map((n) => ({
      id: n.id,
      type: renderKindFor(descriptorsByKey[n.type]),
      position: n.position,
      data: {
        nodeTypeKey: n.type,
        typeVersion: n.typeVersion,
        label: n.name,
        parameters: n.parameters,
        status: 'idle',
        onError: n.onError,
        maxTries: n.maxTries,
        waitBetweenTriesMs: n.waitBetweenTriesMs,
      },
    }))
    const edges: FlowEdge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
    }))
    set({
      workflowId,
      baseVersionId,
      nodes,
      edges,
      viewport: graph.viewport,
      isDirty: false,
      selectedNodeId: null,
      history: { past: [], future: [] },
    })
  },

  markSaved: (baseVersionId) => set({ baseVersionId, isDirty: false }),

  toGraph: () => {
    const { nodes, edges, viewport } = get()
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data.nodeTypeKey,
        typeVersion: n.data.typeVersion,
        name: n.data.label,
        position: n.position,
        parameters: n.data.parameters,
        onError: n.data.onError,
        maxTries: n.data.maxTries,
        waitBetweenTriesMs: n.data.waitBetweenTriesMs,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle ?? null,
        targetHandle: e.targetHandle ?? null,
      })),
      viewport,
    }
  },

  onNodesChange: (changes) => {
    const isCommit = changes.some(
      (c) => c.type === 'remove' || (c.type === 'position' && c.dragging === false),
    )
    set((state) => {
      const next: Partial<CanvasState> = {
        nodes: applyNodeChanges(changes, state.nodes),
        isDirty: true,
      }
      if (isCommit) {
        next.history = {
          past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
          future: [],
        }
      }
      return next
    })
  },

  onEdgesChange: (changes) => {
    const isCommit = changes.some((c) => c.type === 'remove')
    set((state) => {
      const next: Partial<CanvasState> = {
        edges: applyEdgeChanges(changes, state.edges),
        isDirty: true,
      }
      if (isCommit) {
        next.history = {
          past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
          future: [],
        }
      }
      return next
    })
  },

  onConnect: (connection) => {
    set((state) => {
      if (connection.source === connection.target) return state
      const duplicate = state.edges.some(
        (e) =>
          e.source === connection.source &&
          e.target === connection.target &&
          e.sourceHandle === connection.sourceHandle,
      )
      if (duplicate) return state
      return {
        edges: addEdge(connection, state.edges),
        isDirty: true,
        history: {
          past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
          future: [],
        },
      }
    })
  },

  setViewport: (viewport) => set({ viewport }),

  addNode: (descriptor, position, connectFrom) => {
    const id = nextNodeId()
    const node: FlowNode = {
      id,
      type: renderKindFor(descriptor),
      position,
      data: {
        nodeTypeKey: descriptor.key,
        typeVersion: descriptor.version,
        label: null,
        parameters: defaultParameters(descriptor),
        status: 'idle',
        onError: 'stop',
        maxTries: 3,
        waitBetweenTriesMs: 1000,
      },
    }
    set((state) => {
      const newEdges = connectFrom
        ? addEdge(
            {
              id: `e_${connectFrom.nodeId}_${id}`,
              source: connectFrom.nodeId,
              target: id,
              sourceHandle: connectFrom.handle,
              targetHandle: null,
            },
            state.edges,
          )
        : state.edges
      return {
        nodes: [...state.nodes, node],
        edges: newEdges,
        isDirty: true,
        history: {
          past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
          future: [],
        },
      }
    })
    return id
  },

  removeNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      isDirty: true,
      history: {
        past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
        future: [],
      },
    })),

  updateNodeParameters: (nodeId, parameters) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, parameters } } : n,
      ),
      isDirty: true,
      history: {
        past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
        future: [],
      },
    })),

  updateNodeLabel: (nodeId, label) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, label } } : n,
      ),
      isDirty: true,
    })),

  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  applyAutoLayout: (positions) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        positions[n.id] ? { ...n, position: positions[n.id] } : n,
      ),
      isDirty: true,
      history: {
        past: [...state.history.past, snapshot(state)].slice(-MAX_HISTORY),
        future: [],
      },
    })),

  undo: () =>
    set((state) => {
      const previous = state.history.past.at(-1)
      if (!previous) return state
      return {
        nodes: previous.nodes,
        edges: previous.edges,
        isDirty: true,
        history: {
          past: state.history.past.slice(0, -1),
          future: [snapshot(state), ...state.history.future],
        },
      }
    }),

  redo: () =>
    set((state) => {
      const next = state.history.future[0]
      if (!next) return state
      return {
        nodes: next.nodes,
        edges: next.edges,
        isDirty: true,
        history: {
          past: [...state.history.past, snapshot(state)],
          future: state.history.future.slice(1),
        },
      }
    }),

  canUndo: () => get().history.past.length > 0,
  canRedo: () => get().history.future.length > 0,
}))
