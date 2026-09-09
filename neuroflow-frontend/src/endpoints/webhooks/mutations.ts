import { useMutation, useQueryClient } from '@tanstack/react-query'
import { webhookKeys } from './keys'
import { listenForTestWebhook } from './requests'

export function useListenForTestWebhook(workflowId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (nodeId: string) => listenForTestWebhook(workflowId, nodeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: webhookKeys.forWorkflow(workflowId) }),
  })
}
