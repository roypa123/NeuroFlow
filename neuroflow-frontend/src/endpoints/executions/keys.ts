export const executionKeys = {
  all: ['executions'] as const,
  list: (
    projectId: string,
    filters?: { workflowId?: string; status?: string; mode?: string },
  ) => [...executionKeys.all, 'list', projectId, filters ?? {}] as const,
  detail: (id: string) => [...executionKeys.all, 'detail', id] as const,
  nodeData: (id: string, nodeId: string) =>
    [...executionKeys.all, 'detail', id, 'nodes', nodeId] as const,
  stats: (projectId: string) => [...executionKeys.all, 'stats', projectId] as const,
}
