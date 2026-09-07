// One error shape for every response, from every endpoint -- see
// docs/11-api-design.md #11.4 and docs/05-state-and-data-fetching.md #5.3.

export interface ApiErrorDetail {
  field: string
  message: string
  code: string
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: ApiErrorDetail[]
  requestId?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: ApiErrorDetail[]
  readonly requestId?: string

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.details = body.details
    this.requestId = body.requestId
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
