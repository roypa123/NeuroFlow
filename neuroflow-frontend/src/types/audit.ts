import { z } from 'zod'

// Mirrors app/modules/audit/schemas.py.
export const auditLogSchema = z.object({
  id: z.string(),
  organizationId: z.string(),
  actorId: z.string().nullable(),
  action: z.string(),
  resourceType: z.string(),
  resourceId: z.string(),
  changes: z.record(z.string(), z.unknown()).nullable(),
  createdAt: z.string(),
})
export type AuditLog = z.infer<typeof auditLogSchema>
