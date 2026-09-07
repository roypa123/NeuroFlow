import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { registerSessionExpiredHandler, setAccessToken } from '@/api'
import { authKeys, useCurrentUser } from '@/endpoints/auth'
import type { User } from '@/types/auth'

// Session state lives here, not in a Zustand store -- see
// docs/05-state-and-data-fetching.md #5.1's dividing line: this is
// server-known state (who is the current user), fetched via TanStack Query,
// with the access token itself held in api/token-store's in-memory cell.

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  /** Called after a successful login/register mutation. */
  onAuthenticated: (accessToken: string, user: User) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  // No stored access token survives a reload by design
  // (docs/15-security-and-credentials.md #15.2); GET /auth/me fires
  // unconditionally on mount, and a 401 drives exactly one refresh attempt
  // through the normal interceptor path (docs/05 #5.3), which is what
  // resumes a session from the HttpOnly refresh cookie.
  const { data: user, isLoading, isFetched } = useCurrentUser(true)

  useEffect(() => {
    registerSessionExpiredHandler(() => {
      setAccessToken(null)
      queryClient.setQueryData(authKeys.me(), null)
    })
  }, [queryClient])

  const onAuthenticated = useCallback(
    (accessToken: string, nextUser: User) => {
      setAccessToken(accessToken)
      queryClient.setQueryData(authKeys.me(), nextUser)
    },
    [queryClient],
  )

  const signOut = useCallback(() => {
    setAccessToken(null)
    queryClient.setQueryData(authKeys.me(), null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: user ?? null,
      isLoading: isLoading && !isFetched,
      isAuthenticated: Boolean(user),
      onAuthenticated,
      signOut,
    }),
    [user, isLoading, isFetched, onAuthenticated, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
