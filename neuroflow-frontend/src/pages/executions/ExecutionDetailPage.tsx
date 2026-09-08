import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { ArrowLeft, ListChecks, RotateCcw, Square } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ComingSoon } from '@/components/common/ComingSoon'
import { DataView } from '@/components/canvas/inspector/DataView'
import {
  useCancelExecution,
  useExecution,
  useNodeData,
  useRetryExecution,
} from '@/endpoints/executions'
import type { NodeExecutionRead } from '@/types/executions'
import { paths } from '@/routing/paths'

const CANCELABLE_STATUSES = new Set(['queued', 'running', 'waiting'])
const RETRYABLE_STATUSES = new Set(['error', 'canceled'])

export default function ExecutionDetailPage() {
  const { executionId } = useParams<{ executionId: string }>()
  const navigate = useNavigate()
  // Polls while the run is still in flight -- this page has no SSE
  // subscription of its own (that's the live editor's job); a live
  // execution opened directly here just needs to eventually show the
  // final state.
  const { data: execution, isLoading } = useExecution(executionId ?? null, {
    pollWhileActive: true,
  })
  const cancelExecution = useCancelExecution()
  const retryExecution = useRetryExecution()
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null)

  if (!executionId) return null
  if (isLoading || !execution) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading...
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <Button size="icon-sm" variant="ghost" onClick={() => navigate(paths.executions())}>
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold">Execution</h1>
          <p className="text-sm text-muted-foreground">{execution.id}</p>
        </div>
        <Badge
          variant={
            execution.status === 'success'
              ? 'default'
              : execution.status === 'error'
                ? 'destructive'
                : 'outline'
          }
        >
          {execution.status}
        </Badge>
        {CANCELABLE_STATUSES.has(execution.status) && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => cancelExecution.mutate(execution.id)}
            disabled={cancelExecution.isPending}
          >
            <Square className="size-4" />
            Cancel
          </Button>
        )}
        {RETRYABLE_STATUSES.has(execution.status) && (
          <Button
            size="sm"
            onClick={() =>
              retryExecution.mutate(
                { id: execution.id, fromFailedNode: true },
                {
                  onSuccess: (retried) => navigate(paths.executionDetail(retried.id)),
                },
              )
            }
            disabled={retryExecution.isPending}
          >
            <RotateCcw className="size-4" />
            Retry from failed node
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => navigate(paths.workflowEditor(execution.workflowId))}>
          Open workflow
        </Button>
      </div>

      {execution.error && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="space-y-1 p-4">
            <p className="text-sm font-medium text-destructive">
              {execution.error.nodeName ? `${execution.error.nodeName}: ` : ''}
              {execution.error.message}
            </p>
            {execution.error.expression && (
              <p className="font-mono text-xs text-muted-foreground">
                in expression: {execution.error.expression}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {execution.nodes.length === 0 ? (
        <ComingSoon icon={ListChecks} title="No node runs yet" description="Still queued." />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Node</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Items</TableHead>
              <TableHead>Duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {execution.nodes.map((node) => (
              <NodeRunRow
                key={`${node.nodeId}-${node.runIndex}`}
                node={node}
                executionId={execution.id}
                expanded={expandedNodeId === node.nodeId}
                onToggle={() =>
                  setExpandedNodeId((current) => (current === node.nodeId ? null : node.nodeId))
                }
              />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}

function NodeRunRow({
  node,
  executionId,
  expanded,
  onToggle,
}: {
  node: NodeExecutionRead
  executionId: string
  expanded: boolean
  onToggle: () => void
}) {
  const { data: nodeData } = useNodeData(expanded ? executionId : null, expanded ? node.nodeId : null)

  return (
    <>
      <TableRow className="cursor-pointer" onClick={onToggle}>
        <TableCell className="font-medium">{node.nodeName}</TableCell>
        <TableCell>
          <Badge
            variant={
              node.status === 'success'
                ? 'default'
                : node.status === 'error'
                  ? 'destructive'
                  : 'outline'
            }
          >
            {node.status}
          </Badge>
        </TableCell>
        <TableCell className="text-muted-foreground">
          {node.itemsIn ?? 0} in / {node.itemsOut ?? 0} out
        </TableCell>
        <TableCell className="text-muted-foreground">
          {node.durationMs != null ? `${node.durationMs}ms` : '—'}
        </TableCell>
      </TableRow>
      {expanded && (
        <TableRow>
          <TableCell colSpan={4} className="whitespace-normal bg-muted/30">
            {node.error ? (
              <div className="space-y-1 p-2">
                <p className="text-sm font-medium text-destructive">{node.error.message}</p>
                {node.error.expression && (
                  <p className="font-mono text-xs text-muted-foreground">
                    in expression: {node.error.expression}
                  </p>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 p-2">
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Input</p>
                  <DataView items={nodeData?.inputItems ?? []} emptyLabel="No input items." />
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Output</p>
                  <DataView items={nodeData?.outputItems ?? []} emptyLabel="No output items." />
                </div>
              </div>
            )}
          </TableCell>
        </TableRow>
      )}
    </>
  )
}
