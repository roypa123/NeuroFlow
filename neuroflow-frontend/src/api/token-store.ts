// In-memory-only access token holder.
//
// Deliberately NOT localStorage: anything readable by JS is readable by an
// XSS payload. Living in memory means a page reload evicts it (recovered
// via the HttpOnly refresh cookie) and a persistent XSS has to maintain its
// own execution context to keep using it, rather than reading it once from
// storage. See docs/15-security-and-credentials.md #15.2.
//
// A plain module-level variable (not a Zustand store, not React state) is
// deliberate: api/client.ts's interceptor reads/writes it outside of any
// component tree, and it must never be treated as server or UI state --
// see docs/05-state-and-data-fetching.md #5.1.
let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}
