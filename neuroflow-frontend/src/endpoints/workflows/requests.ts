import { z } from 'zod'
import { apiClient } from '@/api'
import {
  keysetPageSchema,
  workflowReadSchema,
  workflowSummarySchema,
  workflowVersionReadSchema,
  type WorkflowGraph,
  type WorkflowRead,
  type WorkflowSettings,
  type WorkflowSummary,
  type WorkflowVersionRead,
} from '@/types/workflows'

const workflowPageSchema = keysetPageSchema(workflowSummarySchema)

export interface WorkflowListParams {
  projectId: string
  search?: string
  isActive?: boolean
  cursor?: string
}

export async function fetchWorkflows(
  params: WorkflowListParams,
): Promise<{ items: WorkflowSummary[]; nextCursor: string | null; hasMore: boolean }> {
  const { data } = await apiClient.get('/workflows', {
    params: {
      projectId: params.projectId,
      search: params.search || undefined,
      isActive: params.isActive,
      cursor: params.cursor,
    },
  })
  return workflowPageSchema.parse(data)
}

export async function fetchWorkflow(id: string): Promise<WorkflowRead> {
  const { data } = await apiClient.get(`/workflows/${id}`)
  return workflowReadSchema.parse(data)
}

export async function createWorkflow(input: {
  projectId: string
  name: string
  description?: string | null
}): Promise<WorkflowRead> {
  const { data } = await apiClient.post('/workflows', input)
  return workflowReadSchema.parse(data)
}

export interface UpdateWorkflowInput {
  name?: string
  description?: string | null
  settings?: WorkflowSettings
  graph?: WorkflowGraph
  baseVersionId?: string | null
  note?: string | null
}

export async function updateWorkflow(
  id: string,
  input: UpdateWorkflowInput,
): Promise<WorkflowRead> {
  const { data } = await apiClient.patch(`/workflows/${id}`, input)
  return workflowReadSchema.parse(data)
}

export async function deleteWorkflow(id: string): Promise<void> {
  await apiClient.delete(`/workflows/${id}`)
}

export async function activateWorkflow(id: string): Promise<WorkflowRead> {
  const { data } = await apiClient.post(`/workflows/${id}/activate`)
  return workflowReadSchema.parse(data)
}

export async function deactivateWorkflow(id: string): Promise<WorkflowRead> {
  const { data } = await apiClient.post(`/workflows/${id}/deactivate`)
  return workflowReadSchema.parse(data)
}

export async function duplicateWorkflow(id: string, name?: string): Promise<WorkflowRead> {
  const { data } = await apiClient.post(`/workflows/${id}/duplicate`, { name })
  return workflowReadSchema.parse(data)
}

export async function fetchWorkflowVersions(id: string): Promise<WorkflowVersionRead[]> {
  const { data } = await apiClient.get(`/workflows/${id}/versions`)
  return z.array(workflowVersionReadSchema).parse(data)
}

export async function restoreWorkflowVersion(
  workflowId: string,
  versionId: string,
): Promise<WorkflowRead> {
  const { data } = await apiClient.post(
    `/workflows/${workflowId}/versions/${versionId}/restore`,
  )
  return workflowReadSchema.parse(data)
}
