import { useMutation, useQueryClient } from '@tanstack/react-query'
import { executionKeys } from './keys'
import { cancelExecution, deleteExecution, executeWorkflow, retryExecution } from './requests'

export function useExecuteWorkflow(workflowId: string) {
  return useMutation({
    mutationFn: () => executeWorkflow(workflowId),
  })
}

export function useCancelExecution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cancelExecution(id),
    onSuccess: (data) => {
      qc.setQueryData(executionKeys.detail(data.id), data)
      qc.invalidateQueries({ queryKey: executionKeys.all })
    },
  })
}

export function useRetryExecution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fromFailedNode }: { id: string; fromFailedNode?: boolean }) =>
      retryExecution(id, fromFailedNode),
    onSuccess: () => qc.invalidateQueries({ queryKey: executionKeys.all }),
  })
}

export function useDeleteExecution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteExecution(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: executionKeys.all }),
  })
}
