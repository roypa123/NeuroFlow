import { apiClient } from '@/api'
import {
  loginResponseSchema,
  userSchema,
  type LoginResponse,
  type User,
} from '@/types/auth'

// Raw async functions: URL + params + zod parse. No React here -- see
// docs/05-state-and-data-fetching.md #5.4.

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post('/auth/login', { email, password })
  return loginResponseSchema.parse(data)
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await apiClient.get('/auth/me')
  return userSchema.parse(data)
}

export async function register(input: {
  email: string
  password: string
  name: string
}): Promise<LoginResponse> {
  const { data } = await apiClient.post('/auth/register', input)
  return loginResponseSchema.parse(data)
}

export async function forgotPassword(email: string): Promise<void> {
  // Always 202 server-side regardless of whether the email exists -- see
  // docs/15-security-and-credentials.md #15.2 (no user enumeration).
  await apiClient.post('/auth/forgot-password', { email })
}
