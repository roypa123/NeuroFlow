import { z } from 'zod'
import { ROLES } from './auth'

// Mirrors docs/11-api-design.md #11.6. See src/types/auth.ts for the
// zod-at-the-boundary rationale.

export const organizationSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.enum(ROLES),
})
export type Organization = z.infer<typeof organizationSchema>

export const memberSchema = z.object({
  userId: z.string(),
  email: z.string(),
  name: z.string(),
  role: z.enum(ROLES),
})
export type Member = z.infer<typeof memberSchema>

export const invitationSchema = z.object({
  id: z.string(),
  organizationId: z.string(),
  email: z.string(),
  role: z.enum(ROLES),
  expiresAt: z.string(),
  // Shown exactly once, in the create-invitation response -- there is no
  // outbound email infra yet, so the inviting admin shares this link by
  // hand. Never returned by any other endpoint.
  token: z.string(),
})
export type Invitation = z.infer<typeof invitationSchema>

export const invitationAcceptResultSchema = z.object({
  organizationId: z.string(),
  role: z.enum(ROLES),
})
export type InvitationAcceptResult = z.infer<typeof invitationAcceptResultSchema>
