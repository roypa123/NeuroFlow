import { useMutation, useQueryClient } from '@tanstack/react-query'
import { projectKeys } from './keys'
import { createProject, deleteProject, updateProject } from './requests'

export function useCreateProject(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createProject({ organizationId, name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.list(organizationId) }),
  })
}

export function useUpdateProject(organizationId: string, projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => updateProject(projectId, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.list(organizationId) })
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useDeleteProject(organizationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => deleteProject(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.list(organizationId) }),
  })
}
