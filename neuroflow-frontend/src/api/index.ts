export { apiClient } from './client'
export { ApiError, isApiError, type ApiErrorBody, type ApiErrorDetail } from './errors'
export { registerSessionExpiredHandler } from './interceptors'
export { getAccessToken, setAccessToken } from './token-store'

// Side-effecting import: wires the interceptors onto apiClient. Importing
// this index module is what actually activates them.
import './interceptors'
