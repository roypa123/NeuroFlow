import { useQuery } from '@tanstack/react-query'
import { apiKeyKeys } from './keys'
import { fetchApiKeys } from './requests'

export function useApiKeys(organizationId: string | null) {
  return useQuery({
    queryKey: apiKeyKeys.list(organizationId ?? ''),
    queryFn: () => fetchApiKeys(organizationId as string),
    enabled: Boolean(organizationId),
  })
}
