import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { workflowKeys } from './keys'
import {
  fetchWorkflow,
  fetchWorkflowVersions,
  fetchWorkflows,
  type WorkflowListParams,
} from './requests'

export function useWorkflows(params: Omit<WorkflowListParams, 'cursor'> | null) {
  return useInfiniteQuery({
    queryKey: params ? workflowKeys.list(params.projectId, params) : workflowKeys.all,
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      fetchWorkflows({ ...(params as WorkflowListParams), cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(params),
  })
}

export function useWorkflow(id: string | null) {
  return useQuery({
    queryKey: workflowKeys.detail(id ?? ''),
    queryFn: () => fetchWorkflow(id as string),
    enabled: Boolean(id),
  })
}

export function useWorkflowVersions(id: string | null) {
  return useQuery({
    queryKey: workflowKeys.versions(id ?? ''),
    queryFn: () => fetchWorkflowVersions(id as string),
    enabled: Boolean(id),
  })
}
