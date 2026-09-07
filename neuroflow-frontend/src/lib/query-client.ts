import { QueryClient } from '@tanstack/react-query'
import { isApiError } from '@/api'

// Defaults and their reasoning are in docs/05-state-and-data-fetching.md #5.5:
// never retry a 4xx (the request is wrong, retrying is pure latency), never
// retry mutations (side effects may have landed), and no
// refetchOnWindowFocus (an editor that silently refetches on alt-tab-back
// is disorienting -- live-ness comes from SSE instead).
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) =>
        isApiError(error) && error.status >= 400 && error.status < 500
          ? false
          : failureCount < 2,
      refetchOnWindowFocus: false,
      throwOnError: false,
    },
    mutations: {
      retry: 0,
    },
  },
})
