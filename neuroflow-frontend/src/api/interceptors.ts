import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { apiClient } from './client'
import { ApiError, type ApiErrorBody } from './errors'
import { getAccessToken, setAccessToken } from './token-store'

// docs/05-state-and-data-fetching.md #5.3:
//   1. Request: attach Authorization + X-Request-Id.
//   2. Response (success): pass through.
//   3. Response (error): normalise into ApiError. On 401 with an expired
//      access token, refresh ONCE (deduplicating concurrent refreshes
//      through a shared promise) and replay. On the second 401, sign out.

let onSessionExpired: (() => void) | null = null

/** AuthProvider registers this once, at mount, so the interceptor can clear
 * the session without importing React/context code. */
export function registerSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  config.headers.set('X-Request-Id', crypto.randomUUID())
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  // A bare axios call, not apiClient: going through apiClient's own
  // interceptors here would risk recursing back into this same function on
  // a failed refresh.
  const response = await axios.post<{ accessToken: string }>(
    `${apiClient.defaults.baseURL}/auth/refresh`,
    {},
    { withCredentials: true },
  )
  const token = response.data.accessToken
  setAccessToken(token)
  return token
}

function toApiError(error: AxiosError<{ error?: ApiErrorBody }>): ApiError {
  const status = error.response?.status ?? 0
  const body = error.response?.data?.error
  if (body) {
    return new ApiError(status, body)
  }
  return new ApiError(status, {
    code: status === 0 ? 'network_error' : 'unknown_error',
    message: error.message || 'An unexpected network error occurred.',
  })
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error?: ApiErrorBody }>) => {
    const config = error.config as RetryableConfig | undefined
    const status = error.response?.status

    const isAuthEndpoint = config?.url?.includes('/auth/')
    if (status === 401 && config && !config._retry && !isAuthEndpoint) {
      config._retry = true
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null
        })
        const token = await refreshPromise
        config.headers.set('Authorization', `Bearer ${token}`)
        return apiClient(config)
      } catch {
        setAccessToken(null)
        onSessionExpired?.()
        return Promise.reject(toApiError(error))
      }
    }

    return Promise.reject(toApiError(error))
  },
)
