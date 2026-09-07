// Query key factory (docs/05-state-and-data-fetching.md #5.4).
export const apiKeyKeys = {
  all: ['api-keys'] as const,
  list: (organizationId: string) => [...apiKeyKeys.all, 'list', organizationId] as const,
}
