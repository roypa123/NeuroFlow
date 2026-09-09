// Every URL is produced by a builder here. No route string literal may
// appear in a component -- see docs/04-frontend-architecture.md #4.6.
export const paths = {
  login: () => '/login',
  signup: () => '/signup',
  forgotPassword: () => '/forgot-password',
  resetPassword: () => '/reset-password',

  home: () => '/',

  acceptInvitation: (token: string) => `/invitations/${token}/accept`,

  workflows: () => '/workflows',
  workflowEditor: (workflowId: string) => `/workflows/${workflowId}`,
  workflowExecution: (workflowId: string, executionId: string) =>
    `/workflows/${workflowId}/executions/${executionId}`,

  agents: () => '/agents',
  agentBuilder: (agentId: string) => `/agents/${agentId}`,

  executions: () => '/executions',
  executionDetail: (executionId: string) => `/executions/${executionId}`,

  credentials: () => '/credentials',
  credentialOAuthCallback: () => '/credentials/oauth/callback',

  settingsProfile: () => '/settings/profile',
  settingsMembers: () => '/settings/members',
  settingsApiKeys: () => '/settings/api-keys',
  settingsAuditLog: () => '/settings/audit-log',
} as const
