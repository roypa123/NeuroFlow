import { memo } from 'react'
import type { NodeProps } from '@xyflow/react'
import type { FlowNode } from '@/store/canvas-store'
import { NodeChrome } from './BaseNode'

function TriggerNodeImpl(props: NodeProps<FlowNode>) {
  return <NodeChrome {...props} shape="trigger" />
}

export const TriggerNode = memo(TriggerNodeImpl)
