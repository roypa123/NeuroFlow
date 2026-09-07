import { useCallback, useRef, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type OnConnectEnd,
  type ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useCanvasStore, type FlowEdge, type FlowNode } from '@/store/canvas-store'
import type { NodeTypeDescriptor } from '@/types/node-types'
import { edgeTypes } from './edges'
import { NodePicker } from './NodePicker'
import { nodeTypes } from './nodes'
import { TidyUpButton } from './TidyUpButton'

// The <ReactFlow> host: handlers, viewport, keybindings --
// docs/06-canvas-and-editor.md #6.3/#6.6. nodeTypes/edgeTypes come from
// module-scope constants (imported, never built here) per performance
// rule #6.12.

const MINIMAP_NODE_LIMIT = 250
const VISIBLE_ELEMENTS_THRESHOLD = 80

interface PendingConnection {
  nodeId: string
  handle: string | null
}

export function FlowCanvas() {
  const nodes = useCanvasStore((s) => s.nodes)
  const edges = useCanvasStore((s) => s.edges)
  const onNodesChange = useCanvasStore((s) => s.onNodesChange)
  const onEdgesChange = useCanvasStore((s) => s.onEdgesChange)
  const onConnect = useCanvasStore((s) => s.onConnect)
  const setViewport = useCanvasStore((s) => s.setViewport)
  const setSelectedNodeId = useCanvasStore((s) => s.setSelectedNodeId)
  const addNode = useCanvasStore((s) => s.addNode)
  const undo = useCanvasStore((s) => s.undo)
  const redo = useCanvasStore((s) => s.redo)

  const { screenToFlowPosition } = useReactFlow()
  const instanceRef = useRef<ReactFlowInstance<FlowNode, FlowEdge> | null>(null)

  const [pickerOpen, setPickerOpen] = useState(false)
  const pickerPosition = useRef({ x: 0, y: 0 })
  const pendingConnection = useRef<PendingConnection | null>(null)

  const openPickerAt = useCallback((x: number, y: number, from?: PendingConnection) => {
    pickerPosition.current = { x, y }
    pendingConnection.current = from ?? null
    setPickerOpen(true)
  }, [])

  const handleConnectEnd: OnConnectEnd = useCallback(
    (event, connectionState) => {
      if (connectionState.isValid || !connectionState.fromNode) return
      const point =
        'clientX' in event
          ? { x: event.clientX, y: event.clientY }
          : { x: event.touches[0].clientX, y: event.touches[0].clientY }
      const flowPosition = screenToFlowPosition(point)
      openPickerAt(flowPosition.x, flowPosition.y, {
        nodeId: connectionState.fromNode.id,
        handle: connectionState.fromHandle?.id ?? null,
      })
    },
    [screenToFlowPosition, openPickerAt],
  )

  const handlePickerSelect = useCallback(
    (descriptor: NodeTypeDescriptor) => {
      addNode(
        descriptor,
        pickerPosition.current,
        pendingConnection.current ?? undefined,
      )
    },
    [addNode],
  )

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const isMod = event.metaKey || event.ctrlKey
      if (event.key === 'Tab' && !isMod) {
        event.preventDefault()
        const bounds = instanceRef.current?.getViewport()
        const center = bounds
          ? screenToFlowPosition({
              x: window.innerWidth / 2,
              y: window.innerHeight / 2,
            })
          : { x: 0, y: 0 }
        openPickerAt(center.x, center.y)
      } else if (isMod && event.key.toLowerCase() === 'z' && event.shiftKey) {
        event.preventDefault()
        redo()
      } else if (isMod && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        undo()
      }
    },
    [openPickerAt, screenToFlowPosition, undo, redo],
  )

  const nodeCount = nodes.length

  return (
    <div className="relative size-full" onKeyDown={handleKeyDown} tabIndex={-1}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectEnd={handleConnectEnd}
        onInit={(instance) => {
          instanceRef.current = instance
        }}
        onMoveEnd={(_event, viewport) => setViewport(viewport)}
        onNodeClick={(_event, node) => setSelectedNodeId(node.id)}
        onNodeDoubleClick={(_event, node) => setSelectedNodeId(node.id)}
        onPaneClick={() => setSelectedNodeId(null)}
        deleteKeyCode={['Backspace', 'Delete']}
        onlyRenderVisibleElements={nodeCount > VISIBLE_ELEMENTS_THRESHOLD}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} />
        <Controls showInteractive={false} />
        {nodeCount <= MINIMAP_NODE_LIMIT && <MiniMap pannable zoomable />}
        <TidyUpButton />
      </ReactFlow>
      <NodePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onSelect={handlePickerSelect}
      />
    </div>
  )
}
