import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { NodeTypeDescriptor } from '@/types/node-types'
import { nodeTypeKeys } from './keys'
import { fetchNodeTypes } from './requests'

// docs/11-api-design.md #11.9: "cached Infinity client-side" -- the
// catalog only changes on a backend deploy.
export function useNodeTypes() {
  return useQuery({
    queryKey: nodeTypeKeys.list(),
    queryFn: fetchNodeTypes,
    staleTime: Infinity,
    gcTime: Infinity,
  })
}

export function useNodeTypesByKey(): Record<string, NodeTypeDescriptor> {
  const { data } = useNodeTypes()
  return useMemo(() => {
    const map: Record<string, NodeTypeDescriptor> = {}
    for (const descriptor of data ?? []) map[descriptor.key] = descriptor
    return map
  }, [data])
}

export function useNodeTypeDescriptor(key: string): NodeTypeDescriptor | undefined {
  return useNodeTypesByKey()[key]
}
