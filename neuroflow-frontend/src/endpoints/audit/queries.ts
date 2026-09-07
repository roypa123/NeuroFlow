import { useQuery } from '@tanstack/react-query'
import { auditKeys } from './keys'
import { fetchAuditLogs } from './requests'

export function useAuditLogs(organizationId: string | null) {
  return useQuery({
    queryKey: auditKeys.list(organizationId ?? ''),
    queryFn: () => fetchAuditLogs(organizationId as string),
    enabled: Boolean(organizationId),
  })
}
