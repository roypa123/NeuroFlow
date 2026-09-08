import { apiClient } from '@/api'
import {
  executionReadSchema,
  executionStatsSchema,
  executionSummarySchema,
  nodeDataReadSchema,
  type ExecutionRead,
  type ExecutionStats,
  type ExecutionSummary,
  type NodeDataRead,
} from '@/types/executions'
import { keysetPageSchema } from '@/types/workflows'

const executionPageSchema = keysetPageSchema(executionSummarySchema)

export interface ExecutionListParams {
  projectId: string
  workflowId?: string
  status?: string
  mode?: string
  cursor?: string
}

export async function fetchExecutions(
  params: ExecutionListParams,
): Promise<{ items: ExecutionSummary[]; nextCursor: string | null; hasMore: boolean }> {
  const { data } = await apiClient.get('/executions', {
    params: {
      projectId: params.projectId,
      workflowId: params.workflowId,
      status: params.status,
      mode: params.mode,
      cursor: params.cursor,
    },
  })
  return executionPageSchema.parse(data)
}

export async function fetchExecution(id: string): Promise<ExecutionRead> {
  const { data } = await apiClient.get(`/executions/${id}`)
  return executionReadSchema.parse(data)
}

export async function fetchNodeData(
  executionId: string,
  nodeId: string,
): Promise<NodeDataRead> {
  const { data } = await apiClient.get(`/executions/${executionId}/nodes/${nodeId}/data`)
  return nodeDataReadSchema.parse(data)
}

export async function executeWorkflow(
  workflowId: string,
): Promise<{ executionId: string }> {
  const { data } = await apiClient.post(`/workflows/${workflowId}/execute`)
  return data as { executionId: string }
}

export async function cancelExecution(id: string): Promise<ExecutionRead> {
  const { data } = await apiClient.post(`/executions/${id}/cancel`)
  return executionReadSchema.parse(data)
}

export async function retryExecution(
  id: string,
  fromFailedNode = true,
): Promise<ExecutionRead> {
  const { data } = await apiClient.post(`/executions/${id}/retry`, {
    fromFailedNode,
  })
  return executionReadSchema.parse(data)
}

export async function deleteExecution(id: string): Promise<void> {
  await apiClient.delete(`/executions/${id}`)
}

export async function fetchExecutionStats(projectId: string): Promise<ExecutionStats> {
  const { data } = await apiClient.get('/executions/stats', { params: { projectId } })
  return executionStatsSchema.parse(data)
}
