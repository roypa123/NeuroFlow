import { z } from 'zod'
import { apiClient } from '@/api'
import { apiKeySchema, apiKeyCreatedSchema, type ApiKey, type ApiKeyCreated } from '@/types/api-keys'

export async function fetchApiKeys(organizationId: string): Promise<ApiKey[]> {
  const { data } = await apiClient.get(`/organizations/${organizationId}/api-keys`)
  return z.array(apiKeySchema).parse(data)
}

export async function createApiKey(
  organizationId: string,
  input: { name: string; scopes: string[]; expiresAt?: string | null },
): Promise<ApiKeyCreated> {
  const { data } = await apiClient.post(`/organizations/${organizationId}/api-keys`, input)
  return apiKeyCreatedSchema.parse(data)
}

export async function revokeApiKey(organizationId: string, keyId: string): Promise<void> {
  await apiClient.delete(`/organizations/${organizationId}/api-keys/${keyId}`)
}
