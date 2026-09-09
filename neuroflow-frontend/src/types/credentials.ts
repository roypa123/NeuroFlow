import { z } from 'zod'
import { nodePropertySchema } from './node-types'

// Mirrors app/modules/credentials/schemas.py + type_registry.py --
// docs/11-api-design.md #11.10. No `data` field anywhere in here, ever --
// see docs/15-security-and-credentials.md #15.6 item 1.

export const credentialSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  name: z.string(),
  type: z.string(),
  oauthExpiresAt: z.string().nullable(),
  lastTestedAt: z.string().nullable(),
  testStatus: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
})
export type Credential = z.infer<typeof credentialSchema>

export const authenticationSpecSchema = z.object({
  type: z.enum(['generic', 'basic']),
  properties: z.record(z.string(), z.record(z.string(), z.string())),
})

export const oauth2SpecSchema = z.object({
  scope: z.string(),
})

export const credentialTypeDescriptorSchema = z.object({
  key: z.string(),
  name: z.string(),
  properties: z.array(nodePropertySchema),
  authenticate: authenticationSpecSchema,
  test: z.object({ method: z.string(), url: z.string() }).nullable(),
  oauth: oauth2SpecSchema.nullable(),
})
export type CredentialTypeDescriptor = z.infer<typeof credentialTypeDescriptorSchema>

export const credentialTestResultSchema = z.object({
  ok: z.boolean(),
  message: z.string().nullable(),
})
export type CredentialTestResult = z.infer<typeof credentialTestResultSchema>

export const oauthAuthorizeResponseSchema = z.object({
  authorizationUrl: z.string(),
})
