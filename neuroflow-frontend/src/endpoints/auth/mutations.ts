import { useMutation, useQueryClient } from '@tanstack/react-query'
import { authKeys } from './keys'
import { forgotPassword, login, logout, register, resetPassword } from './requests'

// A mutation is responsible for its own cache invalidation -- a component
// MUST NOT call invalidateQueries itself. See
// docs/05-state-and-data-fetching.md #5.4.

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: (result) => {
      qc.setQueryData(authKeys.me(), result.user)
    },
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: register,
    onSuccess: (result) => {
      qc.setQueryData(authKeys.me(), result.user)
    },
  })
}

export function useForgotPassword() {
  return useMutation({ mutationFn: forgotPassword })
}

export function useResetPassword() {
  return useMutation({ mutationFn: resetPassword })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      qc.setQueryData(authKeys.me(), null)
      qc.clear()
    },
  })
}
