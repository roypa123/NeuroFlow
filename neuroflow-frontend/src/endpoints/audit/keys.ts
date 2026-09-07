// Query key factory (docs/05-state-and-data-fetching.md #5.4).
export const auditKeys = {
  all: ['audit-logs'] as const,
  list: (organizationId: string) => [...auditKeys.all, 'list', organizationId] as const,
}
