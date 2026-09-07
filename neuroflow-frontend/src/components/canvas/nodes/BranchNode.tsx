import { memo } from 'react'
import type { NodeProps } from '@xyflow/react'
import type { FlowNode } from '@/store/canvas-store'
import { NodeChrome } from './BaseNode'

function BranchNodeImpl(props: NodeProps<FlowNode>) {
  return <NodeChrome {...props} shape="branch" />
}

export const BranchNode = memo(BranchNodeImpl)
