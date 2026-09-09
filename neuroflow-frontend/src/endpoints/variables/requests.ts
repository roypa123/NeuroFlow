import { z } from 'zod'
import { apiClient } from '@/api'
import { variableSchema, type Variable } from '@/types/variables'

export async function fetchVariables(
  organizationId: string,
  projectId?: string | null,
): Promise<Variable[]> {
  const { data } = await apiClient.get('/variables', {
    params: { organizationId, projectId: projectId ?? undefined },
  })
  return z.array(variableSchema).parse(data)
}

export async function createVariable(
  organizationId: string,
  input: { projectId?: string | null; key: string; value: string; isSecret: boolean },
): Promise<Variable> {
  const { data } = await apiClient.post('/variables', input, {
    params: { organizationId },
  })
  return variableSchema.parse(data)
}

export async function updateVariable(
  id: string,
  input: { value?: string; isSecret?: boolean },
): Promise<Variable> {
  const { data } = await apiClient.patch(`/variables/${id}`, input)
  return variableSchema.parse(data)
}

export async function deleteVariable(id: string): Promise<void> {
  await apiClient.delete(`/variables/${id}`)
}
