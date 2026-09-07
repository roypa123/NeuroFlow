// Query key factory (docs/05-state-and-data-fetching.md #5.4). Hierarchical
// so invalidation can be as coarse or precise as needed; ad-hoc inline key
// arrays are banned by review.
export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
}
