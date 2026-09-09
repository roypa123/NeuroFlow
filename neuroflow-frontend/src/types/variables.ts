import { z } from 'zod'

// Mirrors app/modules/variables/schemas.py -- docs/11-api-design.md #11.12.

export const variableSchema = z.object({
  id: z.string(),
  organizationId: z.string(),
  projectId: z.string().nullable(),
  key: z.string(),
  // Absent, not masked, when isSecret -- same structural-absence
  // principle as Credential. See docs/15-security-and-credentials.md
  // #15.6 item 1.
  value: z.string().nullable(),
  isSecret: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
})
export type Variable = z.infer<typeof variableSchema>
