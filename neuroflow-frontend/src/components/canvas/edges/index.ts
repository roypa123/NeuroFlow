import type { EdgeTypes } from '@xyflow/react'
import { FlowEdge } from './FlowEdge'

// Module scope, same reasoning as nodes/index.ts.
export const edgeTypes: EdgeTypes = {
  default: FlowEdge,
}

export { FlowEdge }
