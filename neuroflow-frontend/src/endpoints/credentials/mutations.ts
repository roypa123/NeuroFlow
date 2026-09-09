import { useMutation, useQueryClient } from '@tanstack/react-query'
import { credentialKeys } from './keys'
import {
  completeOAuth,
  createCredential,
  deleteCredential,
  startOAuth,
  testCredential,
  updateCredential,
} from './requests'

export function useCreateCredential() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createCredential,
    onSuccess: () => qc.invalidateQueries({ queryKey: credentialKeys.all }),
  })
}

export function useUpdateCredential(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { name?: string; data?: Record<string, unknown> }) =>
      updateCredential(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: credentialKeys.all }),
  })
}

export function useDeleteCredential() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCredential(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: credentialKeys.all }),
  })
}

export function useTestCredential() {
  return useMutation({
    mutationFn: (id: string) => testCredential(id),
  })
}

export function useStartOAuth() {
  return useMutation({
    mutationFn: ({ id, redirectUri }: { id: string; redirectUri: string }) =>
      startOAuth(id, redirectUri),
  })
}

export function useCompleteOAuth() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ state, code }: { state: string; code: string }) =>
      completeOAuth(state, code),
    onSuccess: () => qc.invalidateQueries({ queryKey: credentialKeys.all }),
  })
}
