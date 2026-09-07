import { useEffect, useMemo } from 'react'
import { useAuth } from '@/context/AuthProvider'
import { useWorkspaceStore } from '@/store/workspace-store'
import type { OrganizationMembership } from '@/types/auth'

/** The organization the user is currently acting in: the persisted choice
 * if it's still one of their memberships, else the first membership on
 * their account. Falling back rather than erroring covers the case where
 * the persisted org was removed, or another member removed this user
 * from it, between sessions. */
export function useCurrentOrganization(): OrganizationMembership | null {
  const { user } = useAuth()
  const currentOrganizationId = useWorkspaceStore((s) => s.currentOrganizationId)
  const setCurrentOrganizationId = useWorkspaceStore((s) => s.setCurrentOrganizationId)

  const organizations = useMemo(() => user?.organizations ?? [], [user])
  const current = useMemo(
    () =>
      organizations.find((org) => org.id === currentOrganizationId) ?? organizations[0] ?? null,
    [organizations, currentOrganizationId],
  )

  useEffect(() => {
    if (current && current.id !== currentOrganizationId) {
      setCurrentOrganizationId(current.id)
    }
  }, [current, currentOrganizationId, setCurrentOrganizationId])

  return current
}
