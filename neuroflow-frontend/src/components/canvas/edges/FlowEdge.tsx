import { memo } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  useReactFlow,
  type EdgeProps,
} from '@xyflow/react'
import { X } from 'lucide-react'

// smoothstep + hover affordances -- docs/06-canvas-and-editor.md #6.5. The
// midpoint `+` (insert-on-edge) lives in FlowCanvas since it opens the
// node picker, which needs canvas-level state; this component owns the
// path, the delete `x`, and the branch-output label.

function FlowEdgeImpl({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  sourceHandleId,
  markerEnd,
}: EdgeProps) {
  const { setEdges } = useReactFlow()
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 8,
  })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={selected ? 'stroke-primary' : undefined}
        style={{ strokeWidth: selected ? 3 : 2 }}
      />
      <EdgeLabelRenderer>
        <div
          className="group nodrag nopan pointer-events-auto absolute flex items-center gap-1"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {sourceHandleId && sourceHandleId !== 'main' && (
            <span className="rounded-full border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {sourceHandleId}
            </span>
          )}
          <button
            type="button"
            aria-label="Delete connection"
            className="flex size-4 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
            onClick={() => setEdges((edges) => edges.filter((e) => e.id !== id))}
          >
            <X className="size-3" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export const FlowEdge = memo(FlowEdgeImpl)
