import { useQuery } from '@tanstack/react-query'
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
