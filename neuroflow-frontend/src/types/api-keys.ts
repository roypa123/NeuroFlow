import { z } from 'zod'

// Mirrors docs/09-domain-modules.md #9.2 and app/modules/auth/schemas.py.
// Scopes are Permission strings from the backend's RBAC matrix
// (app/core/permissions.py) -- kept as a plain string here rather than a
// closed enum, since the frontend doesn't need to validate which scopes
// are legal, only display and round-trip them.

export const apiKeySchema = z.object({
  id: z.string(),
  name: z.string(),
  prefix: z.string(),
  scopes: z.array(z.string()),
  lastUsedAt: z.string().nullable(),
  expiresAt: z.string().nullable(),
  createdAt: z.string(),
})
export type ApiKey = z.infer<typeof apiKeySchema>

export const apiKeyCreatedSchema = apiKeySchema.extend({
  // The raw secret, present ONLY in the create response -- shown once,
  // never returned by list/get. See MembersPage's invite-link pattern for
  // the same "copy it now" UX.
  key: z.string(),
})
export type ApiKeyCreated = z.infer<typeof apiKeyCreatedSchema>

// The scopes a key can plausibly be issued with, from an org-management
// UI -- a curated subset of the full backend Permission enum, not every
// possible value (workflow/agent/credential-execution scopes will be
// added here as those modules land).
export const AVAILABLE_SCOPES = [
  'workflow:read',
  'workflow:write',
  'workflow:execute',
  'execution:read',
  'member:manage',
  'audit:read',
] as const
