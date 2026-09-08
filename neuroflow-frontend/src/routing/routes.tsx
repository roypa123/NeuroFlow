import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { RequireAuth, RequireGuest } from './guards'
import { AppShell } from '@/components/layout/AppShell'
import { SettingsLayout } from '@/components/layout/SettingsLayout'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { paths } from './paths'

// Page components are lazy() so route-level code splitting happens for
// free -- see docs/04-frontend-architecture.md #4.6.
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const SignupPage = lazy(() => import('@/pages/auth/SignupPage'))
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'))
const AcceptInvitationPage = lazy(() => import('@/pages/organizations/AcceptInvitationPage'))

const WorkflowListPage = lazy(() => import('@/pages/workflows/WorkflowListPage'))
const WorkflowEditorPage = lazy(() => import('@/pages/workflows/WorkflowEditorPage'))
const AgentListPage = lazy(() => import('@/pages/agents/AgentListPage'))
const AgentBuilderPage = lazy(() => import('@/pages/agents/AgentBuilderPage'))
const ExecutionListPage = lazy(() => import('@/pages/executions/ExecutionListPage'))
const ExecutionDetailPage = lazy(() => import('@/pages/executions/ExecutionDetailPage'))
const CredentialListPage = lazy(() => import('@/pages/credentials/CredentialListPage'))
const ProfilePage = lazy(() => import('@/pages/settings/ProfilePage'))
const MembersPage = lazy(() => import('@/pages/settings/MembersPage'))
const ApiKeysPage = lazy(() => import('@/pages/settings/ApiKeysPage'))
const AuditLogPage = lazy(() => import('@/pages/settings/AuditLogPage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

function withSuspense(element: React.ReactNode) {
  return (
    <ErrorBoundary>
      <Suspense fallback={null}>{element}</Suspense>
    </ErrorBoundary>
  )
}

function authed(element: React.ReactNode) {
  return withSuspense(
    <RequireAuth>
      <AppShell>{element}</AppShell>
    </RequireAuth>,
  )
}

function settingsPage(element: React.ReactNode) {
  return authed(<SettingsLayout>{element}</SettingsLayout>)
}

export const router = createBrowserRouter([
  {
    path: paths.login(),
    element: withSuspense(
      <RequireGuest>
        <LoginPage />
      </RequireGuest>,
    ),
  },
  {
    path: paths.signup(),
    element: withSuspense(
      <RequireGuest>
        <SignupPage />
      </RequireGuest>,
    ),
  },
  {
    path: paths.forgotPassword(),
    element: withSuspense(
      <RequireGuest>
        <ForgotPasswordPage />
      </RequireGuest>,
    ),
  },
  { path: paths.resetPassword(), element: withSuspense(<ResetPasswordPage />) },
  {
    path: paths.acceptInvitation(':token'),
    element: withSuspense(
      <RequireAuth>
        <AcceptInvitationPage />
      </RequireAuth>,
    ),
  },
  { path: paths.home(), element: <Navigate to={paths.workflows()} replace /> },
  { path: paths.workflows(), element: authed(<WorkflowListPage />) },
  { path: '/workflows/:workflowId', element: authed(<WorkflowEditorPage />) },
  {
    // Reuses the standalone execution detail page rather than a read-only
    // canvas replay -- see this phase's plan's Scope decisions (the
    // canvas-based "run inspection mode" from docs/06-canvas-and-editor.md
    // #6.11 is deferred; ExecutionDetailPage only needs :executionId).
    path: '/workflows/:workflowId/executions/:executionId',
    element: authed(<ExecutionDetailPage />),
  },
  { path: paths.agents(), element: authed(<AgentListPage />) },
  { path: '/agents/:agentId', element: authed(<AgentBuilderPage />) },
  { path: paths.executions(), element: authed(<ExecutionListPage />) },
  { path: '/executions/:executionId', element: authed(<ExecutionDetailPage />) },
  { path: paths.credentials(), element: authed(<CredentialListPage />) },
  { path: paths.settingsProfile(), element: settingsPage(<ProfilePage />) },
  { path: paths.settingsMembers(), element: settingsPage(<MembersPage />) },
  { path: paths.settingsApiKeys(), element: settingsPage(<ApiKeysPage />) },
  { path: paths.settingsAuditLog(), element: settingsPage(<AuditLogPage />) },
  { path: '*', element: withSuspense(<NotFoundPage />) },
])
