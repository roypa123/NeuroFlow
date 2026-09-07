import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import './index.css'
import { AppProviders } from '@/context/AppProviders'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { router } from '@/routing'

// Provider order documented in docs/04-frontend-architecture.md #4.10.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </ErrorBoundary>
  </StrictMode>,
)
