import { memo } from 'react'
import type { NodeProps } from '@xyflow/react'
import type { FlowNode } from '@/store/canvas-store'
import { NodeChrome } from './BaseNode'

function ActionNodeImpl(props: NodeProps<FlowNode>) {
  return <NodeChrome {...props} shape="default" />
}

export const ActionNode = memo(ActionNodeImpl)
