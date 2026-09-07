// Query key factory (docs/05-state-and-data-fetching.md #5.4).
export const organizationKeys = {
  all: ['organizations'] as const,
  list: () => [...organizationKeys.all, 'list'] as const,
  detail: (id: string) => [...organizationKeys.all, 'detail', id] as const,
  members: (id: string) => [...organizationKeys.all, 'detail', id, 'members'] as const,
}
