import { useQuery } from '@tanstack/react-query'
import { variableKeys } from './keys'
import { fetchVariables } from './requests'

export function useVariables(organizationId: string | null, projectId?: string | null) {
  return useQuery({
    queryKey: variableKeys.list(organizationId ?? '', projectId),
    queryFn: () => fetchVariables(organizationId as string, projectId),
    enabled: Boolean(organizationId),
  })
}
