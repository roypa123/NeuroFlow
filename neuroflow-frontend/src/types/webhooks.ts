import { z } from 'zod'

// Mirrors app/modules/webhooks/schemas.py -- docs/11-api-design.md #11.12.

export const webhookRegistrationSchema = z.object({
  id: z.string(),
  nodeId: z.string(),
  path: z.string(),
  method: z.string(),
  isTest: z.boolean(),
  responseMode: z.string(),
  url: z.string(),
})
export type WebhookRegistration = z.infer<typeof webhookRegistrationSchema>
