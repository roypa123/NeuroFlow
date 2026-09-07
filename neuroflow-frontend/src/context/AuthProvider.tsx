import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
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
  // Attempt session resume via the refresh cookie exactly once at boot,
  // before we know whether a session exists at all.
  const [bootAttempted, setBootAttempted] = useState(false)

  const { data: user, isLoading, isFetched } = useCurrentUser(bootAttempted)

  useEffect(() => {
    registerSessionExpiredHandler(() => {
      setAccessToken(null)
      queryClient.setQueryData(authKeys.me(), null)
    })
    // No stored access token survives a reload by design (docs/15 #15.2);
    // the interceptor's refresh path is what resumes a session using the
    // HttpOnly cookie. Triggering /auth/me immediately lets its 401 drive
    // that refresh through the normal interceptor path.
    setBootAttempted(true)
  }, [queryClient])

  const onAuthenticated = (accessToken: string, nextUser: User) => {
    setAccessToken(accessToken)
    queryClient.setQueryData(authKeys.me(), nextUser)
  }

  const signOut = () => {
    setAccessToken(null)
    queryClient.setQueryData(authKeys.me(), null)
    queryClient.clear()
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user: user ?? null,
      isLoading: !bootAttempted || (isLoading && !isFetched),
      isAuthenticated: Boolean(user),
      onAuthenticated,
      signOut,
    }),
    [user, isLoading, isFetched, bootAttempted],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
