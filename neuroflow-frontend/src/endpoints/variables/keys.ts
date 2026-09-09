export const variableKeys = {
  all: ['variables'] as const,
  list: (organizationId: string, projectId?: string | null) =>
    [...variableKeys.all, 'list', organizationId, projectId ?? null] as const,
}
