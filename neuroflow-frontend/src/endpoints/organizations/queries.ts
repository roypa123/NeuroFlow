import { useQuery } from '@tanstack/react-query'
import { organizationKeys } from './keys'
import { fetchMembers, fetchOrganization, fetchOrganizations } from './requests'

export function useOrganizations() {
  return useQuery({ queryKey: organizationKeys.list(), queryFn: fetchOrganizations })
}

export function useOrganization(id: string | null) {
  return useQuery({
    queryKey: organizationKeys.detail(id ?? ''),
    queryFn: () => fetchOrganization(id as string),
    enabled: Boolean(id),
  })
}

export function useMembers(organizationId: string | null) {
  return useQuery({
    queryKey: organizationKeys.members(organizationId ?? ''),
    queryFn: () => fetchMembers(organizationId as string),
    enabled: Boolean(organizationId),
  })
}
