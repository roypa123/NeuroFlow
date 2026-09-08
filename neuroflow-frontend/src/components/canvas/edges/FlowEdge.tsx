import { memo } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  useReactFlow,
  type EdgeProps,
} from '@xyflow/react'
import { X } from 'lucide-react'
import { cn } from 'cn'
import { useNodeRunStatus } from '@/store/execution-store'

// smoothstep + hover affordances -- docs/06-canvas-and-editor.md #6.5. The
// midpoint `+` (insert-on-edge) lives in FlowCanvas since it opens the
// node picker, which needs canvas-level state; this component owns the
// path, the delete `x`, and the branch-output label.
//
// "Running: animated dash flowing source->target" (#6.11) is keyed off
// the *source* node's live status -- once the source finishes, the
// animation stops even if the edge's data hasn't arrived at the target yet.

function FlowEdgeImpl({
  id,
  source,
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
  const sourceStatus = useNodeRunStatus(source)
  const isRunning = sourceStatus === 'running'
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
        className={cn(selected && 'stroke-primary', isRunning && 'stroke-primary')}
        style={{
          strokeWidth: selected || isRunning ? 3 : 2,
          strokeDasharray: isRunning ? '6 4' : undefined,
          animation: isRunning ? 'neuroflow-edge-flow 0.6s linear infinite' : undefined,
        }}
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
