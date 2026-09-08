import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { executionKeys } from './keys'
import {
  fetchExecution,
  fetchExecutionStats,
  fetchExecutions,
  fetchNodeData,
  type ExecutionListParams,
} from './requests'

export function useExecutions(params: Omit<ExecutionListParams, 'cursor'> | null) {
  return useInfiniteQuery({
    queryKey: params ? executionKeys.list(params.projectId, params) : executionKeys.all,
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      fetchExecutions({ ...(params as ExecutionListParams), cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(params),
  })
}

const TERMINAL_STATUSES = new Set(['success', 'error', 'canceled'])
const POLL_INTERVAL_MS = 2000

export function useExecution(id: string | null, options?: { pollWhileActive?: boolean }) {
  return useQuery({
    queryKey: executionKeys.detail(id ?? ''),
    queryFn: () => fetchExecution(id as string),
    enabled: Boolean(id),
    refetchInterval: options?.pollWhileActive
      ? (query) =>
          query.state.data && TERMINAL_STATUSES.has(query.state.data.status)
            ? false
            : POLL_INTERVAL_MS
      : undefined,
  })
}

export function useNodeData(executionId: string | null, nodeId: string | null) {
  return useQuery({
    queryKey: executionKeys.nodeData(executionId ?? '', nodeId ?? ''),
    queryFn: () => fetchNodeData(executionId as string, nodeId as string),
    enabled: Boolean(executionId) && Boolean(nodeId),
  })
}

export function useExecutionStats(projectId: string | null) {
  return useQuery({
    queryKey: executionKeys.stats(projectId ?? ''),
    queryFn: () => fetchExecutionStats(projectId as string),
    enabled: Boolean(projectId),
  })
}
