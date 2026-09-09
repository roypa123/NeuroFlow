import { useQuery } from '@tanstack/react-query'
import { credentialKeys } from './keys'
import { fetchCredentials, fetchCredentialTypes } from './requests'

export function useCredentialTypes() {
  return useQuery({
    queryKey: credentialKeys.types,
    queryFn: fetchCredentialTypes,
    staleTime: Infinity,
  })
}

export function useCredentials(projectId: string | null, type?: string) {
  return useQuery({
    queryKey: credentialKeys.list(projectId ?? '', type),
    queryFn: () => fetchCredentials(projectId as string, type),
    enabled: Boolean(projectId),
  })
}
