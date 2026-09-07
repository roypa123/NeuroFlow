import { z } from 'zod'

// Mirrors docs/11-api-design.md #11.6.

export const projectSchema = z.object({
  id: z.string(),
  organizationId: z.string(),
  name: z.string(),
  isPersonal: z.boolean(),
})
export type Project = z.infer<typeof projectSchema>
