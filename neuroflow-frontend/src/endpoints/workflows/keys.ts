export const workflowKeys = {
  all: ['workflows'] as const,
  list: (projectId: string, filters?: { search?: string; isActive?: boolean }) =>
    [...workflowKeys.all, 'list', projectId, filters ?? {}] as const,
  detail: (id: string) => [...workflowKeys.all, 'detail', id] as const,
  versions: (id: string) => [...workflowKeys.all, 'detail', id, 'versions'] as const,
}
