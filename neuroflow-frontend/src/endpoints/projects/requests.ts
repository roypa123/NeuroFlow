import { z } from 'zod'
import { apiClient } from '@/api'
import { projectSchema, type Project } from '@/types/projects'

export async function fetchProjects(organizationId: string): Promise<Project[]> {
  const { data } = await apiClient.get('/projects', { params: { organizationId } })
  return z.array(projectSchema).parse(data)
}

export async function fetchProject(id: string): Promise<Project> {
  const { data } = await apiClient.get(`/projects/${id}`)
  return projectSchema.parse(data)
}

export async function createProject(input: {
  organizationId: string
  name: string
}): Promise<Project> {
  const { data } = await apiClient.post('/projects', input)
  return projectSchema.parse(data)
}

export async function updateProject(id: string, name: string): Promise<Project> {
  const { data } = await apiClient.patch(`/projects/${id}`, { name })
  return projectSchema.parse(data)
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/projects/${id}`)
}
