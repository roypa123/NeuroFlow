import { z } from 'zod'
import { apiClient } from '@/api'
import { nodeTypeDescriptorSchema, type NodeTypeDescriptor } from '@/types/node-types'

export async function fetchNodeTypes(): Promise<NodeTypeDescriptor[]> {
  const { data } = await apiClient.get('/node-types')
  return z.array(nodeTypeDescriptorSchema).parse(data)
}
