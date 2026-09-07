import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiKeyKeys } from './keys'
import { createApiKey, revokeApiKey } from './requests'

export function useCreateApiKey(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { name: string; scopes: string[]; expiresAt?: string | null }) =>
      createApiKey(organizationId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiKeyKeys.list(organizationId) }),
  })
}

export function useRevokeApiKey(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (keyId: string) => revokeApiKey(organizationId, keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiKeyKeys.list(organizationId) }),
  })
}
