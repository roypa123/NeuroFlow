// Phase 1 risk spike (docs/19-roadmap.md, docs/02-current-state-audit.md #2.3):
// verify @xyflow/react v12 behaves correctly under React 19 StrictMode at a
// canvas size (200 nodes / ~250 edges) representative of a real workflow.
//
// This file is throwaway -- it is not part of the product's routing tree.
// It is mounted only by src/spike/main.tsx for manual/automated verification
// and is deleted once Phase 3 builds the real canvas.
import { useCallback, useMemo, useState } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type Connection,
  type NodeChange,
  type EdgeChange,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

// nodeTypes MUST be defined at module scope (docs/06-canvas-and-editor.md #6.3) --
// an inline object is a new reference every render and remounts every node.
function SpikeNode({ data }: { data: { label: string } }) {
  return (
    <div
      data-testid="spike-node"
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        border: '1px solid #999',
        background: 'white',
        width: 160,
        fontSize: 12,
      }}
    >
      {data.label}
    </div>
  )
}

const nodeTypes: NodeTypes = { spike: SpikeNode }

const GRID_COLS = 20
const NODE_COUNT = 200

function buildInitialNodes(): Node[] {
  return Array.from({ length: NODE_COUNT }, (_, i) => ({
    id: `n${i}`,
    type: 'spike',
    position: { x: (i % GRID_COLS) * 200, y: Math.floor(i / GRID_COLS) * 120 },
    data: { label: `Node ${i}` },
  }))
}

function buildInitialEdges(): Edge[] {
  // ~250 edges: each node connects to the next one in raster order, plus a
  // few cross-row edges, to exercise a non-trivial edge count.
  const edges: Edge[] = []
  for (let i = 0; i < NODE_COUNT - 1; i++) {
    edges.push({ id: `e${i}`, source: `n${i}`, target: `n${i + 1}` })
  }
  for (let i = 0; i < NODE_COUNT - GRID_COLS; i += 4) {
    edges.push({ id: `ec${i}`, source: `n${i}`, target: `n${i + GRID_COLS}` })
  }
  return edges
}

export function ReactFlowSpike() {
  const [nodes, setNodes] = useState<Node[]>(buildInitialNodes)
  const [edges, setEdges] = useState<Edge[]>(buildInitialEdges)
  const [log, setLog] = useState<string[]>([])

  const pushLog = useCallback((line: string) => {
    setLog((prev) => [...prev.slice(-20), line])
  }, [])

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds))
  }, [])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds))
  }, [])

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds))
      pushLog(`connected ${connection.source} -> ${connection.target}`)
    },
    [pushLog],
  )

  // Minimal undo: snapshot node positions before a drag-end, restore on Ctrl+Z.
  const [history, setHistory] = useState<Node[][]>([])
  const onNodeDragStart = useCallback(() => {
    setHistory((h) => [...h, nodes])
  }, [nodes])

  const handleUndo = useCallback(() => {
    setHistory((h) => {
      if (h.length === 0) return h
      const prev = h[h.length - 1]
      setNodes(prev)
      pushLog('undo applied')
      return h.slice(0, -1)
    })
  }, [pushLog])

  const status = useMemo(
    () => `nodes=${nodes.length} edges=${edges.length} historyDepth=${history.length}`,
    [nodes.length, edges.length, history.length],
  )

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div
        data-testid="spike-status"
        style={{ padding: 8, fontFamily: 'monospace', fontSize: 12, background: '#eee' }}
      >
        {status}
        <button data-testid="spike-undo" onClick={handleUndo} style={{ marginLeft: 12 }}>
          Undo (Ctrl+Z)
        </button>
      </div>
      <div style={{ flex: 1 }}>
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStart={onNodeDragStart}
            onlyRenderVisibleElements={nodes.length > 80}
            fitView
          >
            <Background />
            <Controls />
            {nodes.length <= 250 && <MiniMap />}
          </ReactFlow>
        </ReactFlowProvider>
      </div>
      <div data-testid="spike-log" style={{ display: 'none' }}>
        {log.join('\n')}
      </div>
    </div>
  )
}
