// Pure store-logic tests -- no DOM needed, so these run without any
// browser/Playwright dependency (docs/17-testing-strategy.md; this
// sandbox can't reach Playwright's browser-binary CDN, see
// playwright.config.ts). This is what substitutes for a manual browser
// check of the save/reload round trip described in
// docs/19-roadmap.md's Phase 3 exit criterion.
import { beforeEach, describe, expect, it } from 'vitest'
import type { NodeTypeDescriptor } from '@/types/node-types'
import type { WorkflowGraph } from '@/types/workflows'
import { renderKindFor, useCanvasStore } from './canvas-store'

function descriptor(overrides: Partial<NodeTypeDescriptor> = {}): NodeTypeDescriptor {
  return {
    key: 'neuroflow.set',
    version: 1,
    name: 'Set',
    group: 'data',
    category: 'Core',
    description: 'd',
    icon: 'pencil-line',
    color: 'cat-data',
    aliases: [],
    subtitle: null,
    documentationUrl: null,
    inputs: [{ type: 'main', label: null }],
    outputs: [{ type: 'main', label: null }],
    properties: [
      {
        name: 'mode',
        displayName: 'Mode',
        type: 'options',
        default: 'merge',
        required: false,
        description: null,
        placeholder: null,
        options: [{ label: 'Merge', value: 'merge' }],
        loadOptionsMethod: null,
        displayOptions: null,
        typeOptions: null,
        noDataExpression: false,
      },
    ],
    idempotent: true,
    supportsErrorOutput: true,
    maxItems: null,
    ...overrides,
  }
}

const descriptorsByKey: Record<string, NodeTypeDescriptor> = {
  'neuroflow.manualTrigger': descriptor({
    key: 'neuroflow.manualTrigger',
    group: 'trigger',
    inputs: [],
    outputs: [{ type: 'main', label: null }],
  }),
  'neuroflow.set': descriptor(),
  'neuroflow.if': descriptor({
    key: 'neuroflow.if',
    group: 'flow',
    outputs: [
      { type: 'main', label: 'true' },
      { type: 'main', label: 'false' },
    ],
  }),
}

beforeEach(() => {
  useCanvasStore.setState({
    workflowId: null,
    baseVersionId: null,
    nodes: [],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 },
    isDirty: false,
    selectedNodeId: null,
    history: { past: [], future: [] },
  })
})

describe('renderKindFor', () => {
  it('maps trigger-group descriptors to the trigger shape', () => {
    expect(renderKindFor(descriptorsByKey['neuroflow.manualTrigger'])).toBe('trigger')
  })
  it('maps multi-output descriptors to the branch shape', () => {
    expect(renderKindFor(descriptorsByKey['neuroflow.if'])).toBe('branch')
  })
  it('defaults everything else to the action shape', () => {
    expect(renderKindFor(descriptorsByKey['neuroflow.set'])).toBe('action')
  })
  it('falls back to action for an unknown descriptor', () => {
    expect(renderKindFor(undefined)).toBe('action')
  })
})

describe('canvas store: save/reload round trip (Phase 3 exit criterion)', () => {
  it('loadGraph -> toGraph reproduces exactly what was loaded', () => {
    const graph: WorkflowGraph = {
      nodes: [
        {
          id: 'trigger',
          type: 'neuroflow.manualTrigger',
          typeVersion: 1,
          name: null,
          position: { x: 0, y: 0 },
          parameters: {},
          onError: 'stop',
          maxTries: 3,
          waitBetweenTriesMs: 1000,
        },
        {
          id: 'set1',
          type: 'neuroflow.set',
          typeVersion: 1,
          name: 'Reshape',
          position: { x: 200, y: 0 },
          parameters: { mode: 'merge', fields: { a: 1 } },
          onError: 'continue',
          maxTries: 5,
          waitBetweenTriesMs: 2000,
        },
      ],
      edges: [
        {
          id: 'e1',
          source: 'trigger',
          target: 'set1',
          sourceHandle: null,
          targetHandle: null,
        },
      ],
      viewport: { x: 10, y: 20, zoom: 1.5 },
    }

    useCanvasStore.getState().loadGraph('wf1', 'v1', graph, descriptorsByKey)

    expect(useCanvasStore.getState().toGraph()).toEqual(graph)
    expect(useCanvasStore.getState().isDirty).toBe(false)
    expect(useCanvasStore.getState().baseVersionId).toBe('v1')
  })

  it('resolves the node render kind from its descriptor on load', () => {
    useCanvasStore
      .getState()
      .loadGraph(
        'wf1',
        'v1',
        {
          nodes: [
            {
              id: 'trigger',
              type: 'neuroflow.manualTrigger',
              typeVersion: 1,
              name: null,
              position: { x: 0, y: 0 },
              parameters: {},
              onError: 'stop',
              maxTries: 3,
              waitBetweenTriesMs: 1000,
            },
          ],
          edges: [],
          viewport: { x: 0, y: 0, zoom: 1 },
        },
        descriptorsByKey,
      )

    expect(useCanvasStore.getState().nodes[0]?.type).toBe('trigger')
  })
})

describe('canvas store: mutations', () => {
  it('addNode seeds parameters from the descriptor defaults and marks dirty', () => {
    const id = useCanvasStore.getState().addNode(descriptorsByKey['neuroflow.set']!, {
      x: 0,
      y: 0,
    })
    const node = useCanvasStore.getState().nodes.find((n) => n.id === id)
    expect(node?.data.parameters).toEqual({ mode: 'merge' })
    expect(node?.type).toBe('action')
    expect(useCanvasStore.getState().isDirty).toBe(true)
  })

  it('addNode with connectFrom also creates the edge', () => {
    const sourceId = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.manualTrigger']!, { x: 0, y: 0 })
    const targetId = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.set']!, { x: 200, y: 0 }, {
        nodeId: sourceId,
        handle: null,
      })
    const edges = useCanvasStore.getState().edges
    expect(edges).toHaveLength(1)
    expect(edges[0]).toMatchObject({ source: sourceId, target: targetId })
  })

  it('onConnect rejects a self-loop', () => {
    const id = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.set']!, { x: 0, y: 0 })
    useCanvasStore.getState().onConnect({
      source: id,
      target: id,
      sourceHandle: null,
      targetHandle: null,
    })
    expect(useCanvasStore.getState().edges).toHaveLength(0)
  })

  it('onConnect rejects a duplicate edge', () => {
    const a = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.manualTrigger']!, { x: 0, y: 0 })
    const b = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.set']!, { x: 200, y: 0 })
    useCanvasStore
      .getState()
      .onConnect({ source: a, target: b, sourceHandle: null, targetHandle: null })
    useCanvasStore
      .getState()
      .onConnect({ source: a, target: b, sourceHandle: null, targetHandle: null })
    expect(useCanvasStore.getState().edges).toHaveLength(1)
  })

  it('removeNode also removes edges touching it', () => {
    const a = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.manualTrigger']!, { x: 0, y: 0 })
    const b = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.set']!, { x: 200, y: 0 }, {
        nodeId: a,
        handle: null,
      })
    useCanvasStore.getState().removeNode(a)
    expect(useCanvasStore.getState().nodes.map((n) => n.id)).toEqual([b])
    expect(useCanvasStore.getState().edges).toHaveLength(0)
  })

  it('undo/redo restores node positions', () => {
    const id = useCanvasStore
      .getState()
      .addNode(descriptorsByKey['neuroflow.set']!, { x: 0, y: 0 })
    useCanvasStore.getState().onNodesChange([
      { id, type: 'position', position: { x: 300, y: 300 }, dragging: false },
    ])
    expect(useCanvasStore.getState().nodes[0]?.position).toEqual({ x: 300, y: 300 })

    useCanvasStore.getState().undo()
    expect(useCanvasStore.getState().nodes[0]?.position).toEqual({ x: 0, y: 0 })

    useCanvasStore.getState().redo()
    expect(useCanvasStore.getState().nodes[0]?.position).toEqual({ x: 300, y: 300 })
  })

  it('markSaved clears the dirty flag and updates baseVersionId', () => {
    useCanvasStore.getState().addNode(descriptorsByKey['neuroflow.set']!, { x: 0, y: 0 })
    expect(useCanvasStore.getState().isDirty).toBe(true)
    useCanvasStore.getState().markSaved('v2')
    expect(useCanvasStore.getState().isDirty).toBe(false)
    expect(useCanvasStore.getState().baseVersionId).toBe('v2')
  })
})
