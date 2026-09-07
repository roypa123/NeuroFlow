export const nodeTypeKeys = {
  all: ['node-types'] as const,
  list: () => [...nodeTypeKeys.all, 'list'] as const,
}
