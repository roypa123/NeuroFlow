import { z } from 'zod'
import { apiClient } from '@/api'
import { webhookRegistrationSchema, type WebhookRegistration } from '@/types/webhooks'

export async function fetchWorkflowWebhooks(workflowId: string): Promise<WebhookRegistration[]> {
  const { data } = await apiClient.get(`/workflows/${workflowId}/webhooks`)
  return z.array(webhookRegistrationSchema).parse(data)
}

export async function listenForTestWebhook(
  workflowId: string,
  nodeId: string,
): Promise<WebhookRegistration> {
  const { data } = await apiClient.post(`/workflows/${workflowId}/webhooks/test-listen`, {
    nodeId,
  })
  return webhookRegistrationSchema.parse(data)
}
