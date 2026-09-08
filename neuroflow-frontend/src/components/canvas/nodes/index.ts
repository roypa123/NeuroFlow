import type { NodeTypes } from '@xyflow/react'
import { ActionNode } from './ActionNode'
import { BranchNode } from './BranchNode'
import { TriggerNode } from './TriggerNode'

// Defined once at module scope -- docs/06-canvas-and-editor.md #6.12 rule 1:
// an inline object here is a new reference every render and remounts every
// node on the canvas.
export const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  branch: BranchNode,
  action: ActionNode,
}

export { ActionNode, BranchNode, TriggerNode }
