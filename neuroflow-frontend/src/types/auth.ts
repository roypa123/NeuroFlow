import { z } from 'zod'

// Mirrors docs/11-api-design.md #11.5. zod is the source of truth on the
// client -- responses are parsed once at the endpoints/ boundary
// (docs/04-frontend-architecture.md #4.7); past that line, data is trusted.

// erasableSyntaxOnly bans TS enums (docs/21-glossary-and-conventions.md
// #21.3) -- an `as const` array plus a derived union is the replacement.
export const ROLES = ['owner', 'admin', 'member', 'viewer'] as const
export type Role = (typeof ROLES)[number]

export const organizationMembershipSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.enum(ROLES),
})
export type OrganizationMembership = z.infer<typeof organizationMembershipSchema>

export const userSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string(),
  avatarUrl: z.string().nullable().optional(),
  organizations: z.array(organizationMembershipSchema),
})
export type User = z.infer<typeof userSchema>

export const loginResponseSchema = z.object({
  accessToken: z.string(),
  expiresIn: z.number(),
  tokenType: z.string(),
  user: userSchema,
})
export type LoginResponse = z.infer<typeof loginResponseSchema>

export const refreshResponseSchema = z.object({
  accessToken: z.string(),
  expiresIn: z.number(),
  tokenType: z.string(),
})
export type RefreshResponse = z.infer<typeof refreshResponseSchema>
