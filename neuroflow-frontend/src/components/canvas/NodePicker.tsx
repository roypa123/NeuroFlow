import { useMemo } from 'react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { useNodeTypes } from '@/endpoints/node-types'
import type { NodeTypeDescriptor } from '@/types/node-types'
import { iconForName } from './icon-lookup'

// cmdk-powered search palette -- docs/06-canvas-and-editor.md #6.7. Opens
// via Tab, the `+` button, an edge `+`, or dropping a connection on empty
// canvas; grouped by category; searches name/category/aliases/description.

interface NodePickerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (descriptor: NodeTypeDescriptor) => void
}

export function NodePicker({ open, onOpenChange, onSelect }: NodePickerProps) {
  const { data: nodeTypes } = useNodeTypes()

  const byCategory = useMemo(() => {
    const groups = new Map<string, NodeTypeDescriptor[]>()
    for (const descriptor of nodeTypes ?? []) {
      const list = groups.get(descriptor.category) ?? []
      list.push(descriptor)
      groups.set(descriptor.category, list)
    }
    return groups
  }, [nodeTypes])

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add a node"
      description="Search for a node to add to the canvas"
    >
      <CommandInput placeholder="Search nodes... (try 'http', 'gpt', 'if')" />
      <CommandList>
        <CommandEmpty>No matching nodes.</CommandEmpty>
        {[...byCategory.entries()].map(([category, descriptors]) => (
          <CommandGroup key={category} heading={category}>
            {descriptors.map((descriptor) => {
              const Icon = iconForName(descriptor.icon)
              return (
                <CommandItem
                  key={descriptor.key}
                  value={[descriptor.name, descriptor.category, ...descriptor.aliases].join(
                    ' ',
                  )}
                  onSelect={() => {
                    onSelect(descriptor)
                    onOpenChange(false)
                  }}
                >
                  <div
                    className="flex size-6 shrink-0 items-center justify-center rounded"
                    style={{
                      backgroundColor: `color-mix(in oklch, var(--${descriptor.color}) 22%, transparent)`,
                    }}
                  >
                    <Icon className="size-3.5" style={{ color: `var(--${descriptor.color})` }} />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm">{descriptor.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {descriptor.description}
                    </p>
                  </div>
                </CommandItem>
              )
            })}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
