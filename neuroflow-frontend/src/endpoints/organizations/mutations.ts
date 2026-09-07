import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Role } from '@/types/auth'
import { organizationKeys } from './keys'
import {
  acceptInvitation,
  createOrganization,
  inviteMember,
  removeMember,
  updateMemberRole,
  updateOrganization,
} from './requests'

// A mutation is responsible for its own cache invalidation -- see
// docs/05-state-and-data-fetching.md #5.4.

export function useCreateOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createOrganization(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: organizationKeys.list() }),
  })
}

export function useUpdateOrganization(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => updateOrganization(organizationId, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: organizationKeys.list() })
      qc.invalidateQueries({ queryKey: organizationKeys.detail(organizationId) })
    },
  })
}

export function useInviteMember(organizationId: string) {
  return useMutation({
    mutationFn: (input: { email: string; role: Role }) => inviteMember(organizationId, input),
  })
}

export function useUpdateMemberRole(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      updateMemberRole(organizationId, userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: organizationKeys.members(organizationId) }),
  })
}

export function useRemoveMember(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => removeMember(organizationId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: organizationKeys.members(organizationId) }),
  })
}

export function useAcceptInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (token: string) => acceptInvitation(token),
    onSuccess: () => qc.invalidateQueries({ queryKey: organizationKeys.list() }),
  })
}
