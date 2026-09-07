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
  // Usually ApiErrorDetail[] (422 field errors), but some errors carry a
  // single structured object instead -- e.g. workflow.version_conflict's
  // { expectedVersionId, actualVersionId } (docs/11-api-design.md #11.7).
  // Narrow with a schema at the call site rather than assuming the array
  // shape everywhere.
  details?: ApiErrorDetail[] | Record<string, unknown>
  requestId?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: ApiErrorDetail[] | Record<string, unknown>
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
