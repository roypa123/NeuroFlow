import { useEffect, useMemo, useRef } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useNodeTypeDescriptor } from '@/endpoints/node-types'
import { useUiStore } from '@/store/ui-store'
import { useCanvasStore } from '@/store/canvas-store'
import { evaluateDisplayOptions, buildParameterSchema } from './schema'
import { FieldRenderer } from './FieldRenderer'

// The inspector's Params tab -- docs/06-canvas-and-editor.md #6.9. Input/
// Output tabs are empty-state placeholders until Phase 4 wires up real
// execution data (see this phase's plan; the three-column layout collapses
// to these same tabs on narrow viewports per the doc, so building tabs
// first covers both cases).

const DEBOUNCE_MS = 300

export function Inspector() {
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId)
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === s.selectedNodeId))
  const updateNodeParameters = useCanvasStore((s) => s.updateNodeParameters)
  const updateNodeLabel = useCanvasStore((s) => s.updateNodeLabel)
  const removeNode = useCanvasStore((s) => s.removeNode)
  const setSelectedNodeId = useCanvasStore((s) => s.setSelectedNodeId)
  const activeTab = useUiStore((s) => s.activeInspectorTab)
  const setActiveTab = useUiStore((s) => s.setActiveInspectorTab)

  const descriptor = useNodeTypeDescriptor(node?.data.nodeTypeKey ?? '')
  const schema = useMemo(
    () => buildParameterSchema(descriptor?.properties ?? []),
    [descriptor],
  )

  const form = useForm({
    resolver: zodResolver(schema),
    values: node?.data.parameters ?? {},
  })
  const values = form.watch()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!node) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      updateNodeParameters(node.id, values)
    }, DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(values), node?.id])

  if (!selectedNodeId || !node) {
    return (
      <div className="flex size-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
        Select a node to configure it.
      </div>
    )
  }

  const visibleProperties = (descriptor?.properties ?? []).filter((prop) =>
    evaluateDisplayOptions(prop.displayOptions ?? null, values),
  )

  return (
    <div className="flex size-full flex-col">
      <div className="flex items-center gap-2 border-b border-border p-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs text-muted-foreground">
            {descriptor?.name ?? node.data.nodeTypeKey}
          </p>
          <Input
            value={node.data.label ?? descriptor?.name ?? ''}
            onChange={(e) => updateNodeLabel(node.id, e.target.value)}
            className="h-7 border-none px-0 text-sm font-medium shadow-none focus-visible:ring-0"
          />
        </div>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          onClick={() => {
            removeNode(node.id)
            setSelectedNodeId(null)
          }}
          aria-label="Delete node"
        >
          <Trash2 className="size-4" />
        </Button>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as 'params' | 'input' | 'output')}
        className="flex min-h-0 flex-1 flex-col"
      >
        <TabsList className="mx-3 mt-2">
          <TabsTrigger value="input">Input</TabsTrigger>
          <TabsTrigger value="params">Params</TabsTrigger>
          <TabsTrigger value="output">Output</TabsTrigger>
        </TabsList>
        <TabsContent value="input" className="flex-1 overflow-y-auto p-4">
          <EmptyDataState />
        </TabsContent>
        <TabsContent value="params" className="flex-1 space-y-4 overflow-y-auto p-4">
          {visibleProperties.length === 0 ? (
            <p className="text-sm text-muted-foreground">This node has no parameters.</p>
          ) : (
            visibleProperties.map((property) => (
              <FieldRenderer key={property.name} property={property} control={form.control} />
            ))
          )}
        </TabsContent>
        <TabsContent value="output" className="flex-1 overflow-y-auto p-4">
          <EmptyDataState />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function EmptyDataState() {
  return (
    <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
      Run the workflow to see data here.
      <br />
      Available once execution ships.
    </div>
  )
}
