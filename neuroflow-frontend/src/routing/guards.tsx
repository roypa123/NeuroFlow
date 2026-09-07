import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from '@/context/AuthProvider'
import { paths } from './paths'

// Guards are components, not loader side effects, so they are testable in
// isolation and render a real skeleton while the session resolves -- see
// docs/04-frontend-architecture.md #4.6.
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Loading...
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to={paths.login()} state={{ from: location }} replace />
  }

  return <>{children}</>
}

export function RequireGuest({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null
  if (isAuthenticated) return <Navigate to={paths.home()} replace />

  return <>{children}</>
}
