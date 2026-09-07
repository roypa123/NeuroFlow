// Query key factory (docs/05-state-and-data-fetching.md #5.4).
export const projectKeys = {
  all: ['projects'] as const,
  list: (organizationId: string) => [...projectKeys.all, 'list', organizationId] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
}
