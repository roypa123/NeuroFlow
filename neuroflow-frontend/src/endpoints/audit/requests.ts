import { z } from 'zod'
import { apiClient } from '@/api'
import { auditLogSchema, type AuditLog } from '@/types/audit'

export async function fetchAuditLogs(organizationId: string): Promise<AuditLog[]> {
  const { data } = await apiClient.get('/audit-logs', { params: { organizationId } })
  return z.array(auditLogSchema).parse(data)
}
