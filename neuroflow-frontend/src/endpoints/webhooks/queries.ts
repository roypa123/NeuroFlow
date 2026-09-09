import { useQuery } from '@tanstack/react-query'
import { webhookKeys } from './keys'
import { fetchWorkflowWebhooks } from './requests'

export function useWorkflowWebhooks(workflowId: string | null, isActive: boolean) {
  return useQuery({
    queryKey: webhookKeys.forWorkflow(workflowId ?? ''),
    queryFn: () => fetchWorkflowWebhooks(workflowId as string),
    enabled: Boolean(workflowId) && isActive,
  })
}
