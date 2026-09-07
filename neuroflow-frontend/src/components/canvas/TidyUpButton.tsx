import { useState } from 'react'
import { Panel, useReactFlow } from '@xyflow/react'
import { LayoutGrid } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCanvasStore } from '@/store/canvas-store'

// elkjs is dynamically imported -- docs/06-canvas-and-editor.md #6.12 rule
// 8 -- and only used here, so the ~600KB layout engine never loads unless
// the user actually asks to tidy up.

const NODE_WIDTH = 240
const NODE_HEIGHT = 76

export function TidyUpButton() {
  const nodes = useCanvasStore((s) => s.nodes)
  const edges = useCanvasStore((s) => s.edges)
  const applyAutoLayout = useCanvasStore((s) => s.applyAutoLayout)
  const { fitView } = useReactFlow()
  const [running, setRunning] = useState(false)

  async function tidyUp() {
    if (nodes.length === 0) return
    setRunning(true)
    try {
      const ELK = (await import('elkjs/lib/elk.bundled.js')).default
      const elk = new ELK()
      const graph = {
        id: 'root',
        layoutOptions: {
          'elk.algorithm': 'layered',
          'elk.direction': 'RIGHT',
          'elk.spacing.nodeNode': '64',
          'elk.layered.spacing.nodeNodeBetweenLayers': '120',
          'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
        },
        children: nodes.map((n) => ({ id: n.id, width: NODE_WIDTH, height: NODE_HEIGHT })),
        edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
      }
      const layout = await elk.layout(graph)
      const positions: Record<string, { x: number; y: number }> = {}
      for (const child of layout.children ?? []) {
        positions[child.id] = { x: child.x ?? 0, y: child.y ?? 0 }
      }
      applyAutoLayout(positions)
      requestAnimationFrame(() => fitView({ duration: 300 }))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Panel position="top-right">
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={running}
        onClick={tidyUp}
        title="Tidy up (Ctrl/Cmd+Shift+L)"
      >
        <LayoutGrid className="size-4" />
        Tidy up
      </Button>
    </Panel>
  )
}
