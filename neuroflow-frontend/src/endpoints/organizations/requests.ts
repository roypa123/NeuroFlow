import { z } from 'zod'
import { apiClient } from '@/api'
import type { Role } from '@/types/auth'
import {
  organizationSchema,
  memberSchema,
  invitationSchema,
  invitationAcceptResultSchema,
  type Organization,
  type Member,
  type Invitation,
  type InvitationAcceptResult,
} from '@/types/organizations'

// Raw async functions: URL + params + zod parse. No React here -- see
// docs/05-state-and-data-fetching.md #5.4.

export async function fetchOrganizations(): Promise<Organization[]> {
  const { data } = await apiClient.get('/organizations')
  return z.array(organizationSchema).parse(data)
}

export async function fetchOrganization(id: string): Promise<Organization> {
  const { data } = await apiClient.get(`/organizations/${id}`)
  return organizationSchema.parse(data)
}

export async function createOrganization(name: string): Promise<Organization> {
  const { data } = await apiClient.post('/organizations', { name })
  return organizationSchema.parse(data)
}

export async function updateOrganization(id: string, name: string): Promise<Organization> {
  const { data } = await apiClient.patch(`/organizations/${id}`, { name })
  return organizationSchema.parse(data)
}

export async function fetchMembers(organizationId: string): Promise<Member[]> {
  const { data } = await apiClient.get(`/organizations/${organizationId}/members`)
  return z.array(memberSchema).parse(data)
}

export async function inviteMember(
  organizationId: string,
  input: { email: string; role: Role },
): Promise<Invitation> {
  const { data } = await apiClient.post(`/organizations/${organizationId}/invitations`, input)
  return invitationSchema.parse(data)
}

export async function updateMemberRole(
  organizationId: string,
  userId: string,
  role: Role,
): Promise<Member> {
  const { data } = await apiClient.patch(`/organizations/${organizationId}/members/${userId}`, {
    role,
  })
  return memberSchema.parse(data)
}

export async function removeMember(organizationId: string, userId: string): Promise<void> {
  await apiClient.delete(`/organizations/${organizationId}/members/${userId}`)
}

export async function acceptInvitation(token: string): Promise<InvitationAcceptResult> {
  const { data } = await apiClient.post(`/invitations/${token}/accept`)
  return invitationAcceptResultSchema.parse(data)
}
