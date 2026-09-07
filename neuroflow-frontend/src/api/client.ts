import axios from 'axios'
import { env } from '@/config/env'
import { HTTP_TIMEOUT_MS } from '@/config/constants'

// The single axios instance. Components never import this directly --
// they go through endpoints/ hooks. See docs/04-frontend-architecture.md #4.5.
export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: HTTP_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // carries the HttpOnly refresh cookie
})
