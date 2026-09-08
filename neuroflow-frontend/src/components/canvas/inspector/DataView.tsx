import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ItemRead } from '@/types/executions'

// A JSON-tree rendering of item data -- the "JSON" mode from
// docs/06-canvas-and-editor.md #6.10's four-mode DataView. Table/Schema/
// Binary modes are deferred (see this phase's plan's Scope decisions):
// nothing in the six Phase 4 nodes needs a binary panel, and a JSON tree
// already makes "what did this node actually receive/produce" answerable,
// which is what the exit criterion's diagnosability requirement needs.

export function DataView({ items, emptyLabel }: { items: ItemRead[]; emptyLabel: string }) {
  if (items.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
        {emptyLabel}
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {items.length} item{items.length === 1 ? '' : 's'}
      </p>
      {items.map((item, index) => (
        <JsonNode key={index} label={`Item ${index}`} value={item.json} defaultOpen />
      ))}
    </div>
  )
}

function JsonNode({
  label,
  value,
  defaultOpen = false,
}: {
  label: string
  value: unknown
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const isExpandable =
    value !== null && typeof value === 'object' && Object.keys(value).length > 0

  if (!isExpandable) {
    return (
      <div className="flex gap-1 pl-4 font-mono text-xs">
        <span className="text-muted-foreground">{label}:</span>
        <span className="break-all">{formatPrimitive(value)}</span>
      </div>
    )
  }

  const entries = Array.isArray(value)
    ? value.map((v, i) => [String(i), v] as const)
    : Object.entries(value as Record<string, unknown>)

  return (
    <div className="font-mono text-xs">
      <button
        type="button"
        className="flex items-center gap-1 rounded px-1 hover:bg-accent"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        <span className="text-muted-foreground">{label}</span>
        <span className="text-muted-foreground/70">
          {Array.isArray(value) ? `Array(${value.length})` : `Object`}
        </span>
      </button>
      {open && (
        <div className="ml-3 space-y-0.5 border-l border-border pl-2">
          {entries.map(([key, v]) => (
            <JsonNode key={key} label={key} value={v} />
          ))}
        </div>
      )}
    </div>
  )
}

function formatPrimitive(value: unknown): string {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return `"${value}"`
  return String(value)
}
