export const webhookKeys = {
  all: ['webhooks'] as const,
  forWorkflow: (workflowId: string) => [...webhookKeys.all, workflowId] as const,
}
