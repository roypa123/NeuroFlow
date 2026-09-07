import { useMutation, useQueryClient } from '@tanstack/react-query'
import { workflowKeys } from './keys'
import {
  activateWorkflow,
  createWorkflow,
  deactivateWorkflow,
  deleteWorkflow,
  duplicateWorkflow,
  restoreWorkflowVersion,
  updateWorkflow,
  type UpdateWorkflowInput,
} from './requests'

export function useCreateWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { name: string; description?: string | null }) =>
      createWorkflow({ projectId, ...input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }),
  })
}

// No onSuccess invalidation here: the editor page owns the response
// directly (it needs the new baseVersionId/graph immediately, not a
// refetch) and updates the query cache itself via setQueryData.
export function useUpdateWorkflow(id: string) {
  return useMutation({
    mutationFn: (input: UpdateWorkflowInput) => updateWorkflow(id, input),
  })
}

export function useDeleteWorkflow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteWorkflow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }),
  })
}

export function useActivateWorkflow(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => activateWorkflow(id),
    onSuccess: (data) => {
      qc.setQueryData(workflowKeys.detail(id), data)
      qc.invalidateQueries({ queryKey: workflowKeys.all })
    },
  })
}

export function useDeactivateWorkflow(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => deactivateWorkflow(id),
    onSuccess: (data) => {
      qc.setQueryData(workflowKeys.detail(id), data)
      qc.invalidateQueries({ queryKey: workflowKeys.all })
    },
  })
}

export function useDuplicateWorkflow(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name?: string) => duplicateWorkflow(id, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }),
  })
}

export function useRestoreWorkflowVersion(workflowId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (versionId: string) => restoreWorkflowVersion(workflowId, versionId),
    onSuccess: (data) => {
      qc.setQueryData(workflowKeys.detail(workflowId), data)
      qc.invalidateQueries({ queryKey: workflowKeys.versions(workflowId) })
    },
  })
}
