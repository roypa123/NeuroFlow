import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { cn } from '@/lib/utils'
import { paths } from '@/routing/paths'

const SETTINGS_NAV = [
  { label: 'Profile', to: paths.settingsProfile() },
  { label: 'Members', to: paths.settingsMembers() },
  { label: 'API keys', to: paths.settingsApiKeys() },
  { label: 'Audit log', to: paths.settingsAuditLog() },
] as const

// Shared chrome for every /settings/* page -- plain route links styled as
// tabs, not the Tabs primitive: that component owns which panel is
// mounted internally, which doesn't fit pages that are actually separate
// routes (each lazy-loaded, each with its own URL).
export function SettingsLayout({ children }: { children: ReactNode }) {
  const location = useLocation()

  return (
    <div className="mx-auto max-w-3xl p-6">
      <nav className="mb-6 flex gap-1 border-b" aria-label="Settings">
        {SETTINGS_NAV.map(({ label, to }) => (
          <Link
            key={to}
            to={to}
            className={cn(
              'border-b-2 px-3 py-2 text-sm font-medium transition-colors',
              location.pathname === to
                ? 'border-foreground text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  )
}
