/* eslint-disable react-hooks/static-components --
   Descriptor-driven icon-by-name lookup (docs/13-node-catalog-and-sdk.md
   #13.2) resolves a stable reference into lucide's own icon map; the
   compiler's heuristic can't distinguish that from a component defined
   inline, but nothing is actually created per render here. */
import { useMemo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { cn } from 'cn'
import { useNodeTypeDescriptor } from '@/endpoints/node-types'
import type { FlowNode } from '@/store/canvas-store'
import { useNodeRunSummary } from '@/store/execution-store'
import { useUiStore } from '@/store/ui-store'
import { iconForName } from '../icon-lookup'

// Shared chrome for every node kind -- docs/06-canvas-and-editor.md #6.4.
// 240x76px fixed size, icon tinted by category colour, status ring on the
// left border, subtitle is a cheap static resolution of
// `{{ $parameter.x }}` against current params. The status ring and run
// summary strip come from execution-store (live SSE state), not
// canvas-store -- a node's "how did the last run go" is per-run session
// state, not part of the saved graph.

const STATUS_RING: Record<string, string> = {
  idle: 'border-l-border',
  running: 'border-l-primary animate-pulse',
  success: 'border-l-success',
  error: 'border-l-destructive',
  skipped: 'border-l-muted-foreground opacity-60',
}

function resolveSubtitle(
  template: string | null | undefined,
  parameters: Record<string, unknown>,
): string | null {
  if (!template) return null
  const resolved = template
    .replace(/^=/, '')
    .replace(/\{\{\s*\$parameter\.(\w+)\s*\}\}/g, (_match, name: string) => {
      const value = parameters[name]
      return value === undefined || value === null ? '' : String(value)
    })
  return resolved.trim() || null
}

function outputHandleTop(index: number, total: number): string {
  if (total <= 1) return '50%'
  const step = 100 / (total + 1)
  return `${step * (index + 1)}%`
}

export function NodeChrome({
  id,
  data,
  selected,
  shape,
}: NodeProps<FlowNode> & { shape: 'trigger' | 'branch' | 'default' }) {
  const descriptor = useNodeTypeDescriptor(data.nodeTypeKey)
  const Icon = useMemo(() => iconForName(descriptor?.icon ?? 'box'), [descriptor?.icon])
  const title = data.label || descriptor?.name || data.nodeTypeKey
  const subtitle = resolveSubtitle(descriptor?.subtitle, data.parameters)
  const outputs = descriptor?.outputs ?? [{ type: 'main', label: null }]
  const hasInput = (descriptor?.inputs.length ?? 1) > 0
  const run = useNodeRunSummary(id)
  const status = run?.status ?? 'idle'
  const setActiveInspectorTab = useUiStore((s) => s.setActiveInspectorTab)

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${title}, ${descriptor?.name ?? data.nodeTypeKey}, ${status}`}
      className={cn(
        'flex h-[76px] w-[240px] flex-col justify-center gap-1 border border-border border-l-[3px]',
        'bg-card px-3 py-2 shadow-sm transition-shadow',
        shape === 'trigger' ? 'rounded-l-full rounded-r-md' : 'rounded-md',
        STATUS_RING[status],
        selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background',
      )}
    >
      {hasInput && (
        <Handle
          id="main"
          type="target"
          position={Position.Left}
          className="!size-3 !border-2 !border-background !bg-muted-foreground"
        />
      )}
      <div className="flex items-center gap-2 overflow-hidden">
        <div
          className="flex size-8 shrink-0 items-center justify-center rounded-md"
          style={{ backgroundColor: `color-mix(in oklch, var(--${descriptor?.color ?? 'cat-app'}) 22%, transparent)` }}
        >
          <Icon
            className="size-4"
            style={{ color: `var(--${descriptor?.color ?? 'cat-app'})` }}
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium" title={title}>
            {title}
          </p>
          {run && (run.status === 'success' || run.status === 'error') ? (
            <button
              type="button"
              className="nodrag truncate text-left text-xs text-muted-foreground hover:text-foreground hover:underline"
              onClick={(event) => {
                event.stopPropagation()
                setActiveInspectorTab('output')
              }}
            >
              {run.status === 'success' ? '✓' : '⚠'}{' '}
              {run.durationMs != null ? `${(run.durationMs / 1000).toFixed(1)}s` : ''}
              {run.itemsOut != null ? ` · ${run.itemsOut} items` : ''}
            </button>
          ) : (
            subtitle && (
              <p className="truncate text-xs text-muted-foreground" title={subtitle}>
                {subtitle}
              </p>
            )
          )}
        </div>
      </div>
      {outputs.map((output, index) => (
        <Handle
          key={output.label ?? `main-${index}`}
          id={output.label ?? 'main'}
          type="source"
          position={Position.Right}
          style={{ top: outputHandleTop(index, outputs.length) }}
          className="!size-3 !border-2 !border-background !bg-muted-foreground"
        >
          {shape === 'branch' && output.label && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[10px] font-medium text-muted-foreground">
              {output.label}
            </span>
          )}
        </Handle>
      ))}
    </div>
  )
}
