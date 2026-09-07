import { useQuery } from '@tanstack/react-query'
import { authKeys } from './keys'
import { fetchCurrentUser } from './requests'

export function useCurrentUser(enabled: boolean) {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: fetchCurrentUser,
    enabled,
    staleTime: 5 * 60_000,
    retry: false, // an expired/absent session is not a transient failure
  })
}
