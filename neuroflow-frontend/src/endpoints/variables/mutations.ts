import { useMutation, useQueryClient } from '@tanstack/react-query'
import { variableKeys } from './keys'
import { createVariable, deleteVariable, updateVariable } from './requests'

export function useCreateVariable(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      projectId?: string | null
      key: string
      value: string
      isSecret: boolean
    }) => createVariable(organizationId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: variableKeys.all }),
  })
}

export function useUpdateVariable(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { value?: string; isSecret?: boolean }) => updateVariable(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: variableKeys.all }),
  })
}

export function useDeleteVariable() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteVariable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: variableKeys.all }),
  })
}
