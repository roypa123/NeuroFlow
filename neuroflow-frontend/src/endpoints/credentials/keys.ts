export const credentialKeys = {
  all: ['credentials'] as const,
  list: (projectId: string, type?: string) =>
    [...credentialKeys.all, 'list', projectId, type ?? null] as const,
  detail: (id: string) => [...credentialKeys.all, 'detail', id] as const,
  types: ['credentialTypes'] as const,
}
