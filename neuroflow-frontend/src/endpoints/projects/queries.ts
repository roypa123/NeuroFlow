import { useQuery } from '@tanstack/react-query'
import { projectKeys } from './keys'
import { fetchProject, fetchProjects } from './requests'

export function useProjects(organizationId: string | null) {
  return useQuery({
    queryKey: projectKeys.list(organizationId ?? ''),
    queryFn: () => fetchProjects(organizationId as string),
    enabled: Boolean(organizationId),
  })
}

export function useProject(id: string | null) {
  return useQuery({
    queryKey: projectKeys.detail(id ?? ''),
    queryFn: () => fetchProject(id as string),
    enabled: Boolean(id),
  })
}
