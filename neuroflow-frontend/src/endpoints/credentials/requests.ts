import { z } from 'zod'
import { apiClient } from '@/api'
import {
  credentialSchema,
  credentialTestResultSchema,
  credentialTypeDescriptorSchema,
  oauthAuthorizeResponseSchema,
  type Credential,
  type CredentialTestResult,
  type CredentialTypeDescriptor,
} from '@/types/credentials'

export async function fetchCredentialTypes(): Promise<CredentialTypeDescriptor[]> {
  const { data } = await apiClient.get('/credential-types')
  return z.array(credentialTypeDescriptorSchema).parse(data)
}

export async function fetchCredentials(
  projectId: string,
  type?: string,
): Promise<Credential[]> {
  const { data } = await apiClient.get('/credentials', {
    params: { projectId, type },
  })
  return z.array(credentialSchema).parse(data)
}

export async function createCredential(input: {
  projectId: string
  name: string
  type: string
  data: Record<string, unknown>
}): Promise<Credential> {
  const { data } = await apiClient.post('/credentials', input)
  return credentialSchema.parse(data)
}

export async function updateCredential(
  id: string,
  input: { name?: string; data?: Record<string, unknown> },
): Promise<Credential> {
  const { data } = await apiClient.patch(`/credentials/${id}`, input)
  return credentialSchema.parse(data)
}

export async function deleteCredential(id: string): Promise<void> {
  await apiClient.delete(`/credentials/${id}`)
}

export async function testCredential(id: string): Promise<CredentialTestResult> {
  const { data } = await apiClient.post(`/credentials/${id}/test`)
  return credentialTestResultSchema.parse(data)
}

export async function startOAuth(id: string, redirectUri: string): Promise<string> {
  const { data } = await apiClient.get(`/credentials/${id}/oauth/authorize`, {
    params: { redirectUri },
  })
  return oauthAuthorizeResponseSchema.parse(data).authorizationUrl
}

export async function completeOAuth(state: string, code: string): Promise<Credential> {
  const { data } = await apiClient.post('/credentials/oauth/callback', { state, code })
  return credentialSchema.parse(data)
}
