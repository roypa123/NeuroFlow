import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { ListChecks } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent } from '@/components/ui/card'
import { ComingSoon } from '@/components/common/ComingSoon'
import { useExecutions } from '@/endpoints/executions'
import { useProjects } from '@/endpoints/projects'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'
import type { ExecutionStatus } from '@/types/executions'
import { paths } from '@/routing/paths'

const STATUS_VARIANT: Record<ExecutionStatus, 'default' | 'destructive' | 'outline' | 'secondary'> = {
  queued: 'outline',
  running: 'secondary',
  success: 'default',
  error: 'destructive',
  canceled: 'outline',
  waiting: 'secondary',
}

function formatDuration(ms: number | null): string {
  if (ms == null) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function ExecutionListPage() {
  const currentOrganization = useCurrentOrganization()
  if (!currentOrganization) {
    return (
      <ComingSoon
        icon={ListChecks}
        title="Executions"
        description="Join or create an organization first."
      />
    )
  }
  return <ExecutionListPageContent organizationId={currentOrganization.id} />
}

function ExecutionListPageContent({ organizationId }: { organizationId: string }) {
  const navigate = useNavigate()
  const { data: projects } = useProjects(organizationId)
  const [projectId, setProjectId] = useState<string | null>(null)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const activeProjectId = projectId ?? projects?.[0]?.id ?? null

  const { data, isLoading } = useExecutions(
    activeProjectId ? { projectId: activeProjectId, status } : null,
  )
  const executions = useMemo(() => data?.pages.flatMap((page) => page.items) ?? [], [data])

  if (projects && projects.length === 0) {
    return (
      <ComingSoon
        icon={ListChecks}
        title="Executions"
        description="Create a project and run a workflow first."
      />
    )
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold">Executions</h1>
        <p className="text-sm text-muted-foreground">
          Every run of every workflow in this project.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* '' rather than `undefined` when unset -- see the identical note
            in WorkflowListPage.tsx: Base UI's Select locks its
            controlled-vs-uncontrolled mode on its own first render and
            never revisits it. */}
        {projects && projects.length > 1 && (
          <Select value={activeProjectId ?? ''} onValueChange={setProjectId}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Project" />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select
          value={status ?? 'all'}
          onValueChange={(v) => setStatus(!v || v === 'all' ? undefined : v)}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {(['queued', 'running', 'success', 'error', 'canceled', 'waiting'] as const).map(
              (s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : executions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <ListChecks className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No executions yet.</p>
          </CardContent>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {executions.map((execution) => (
              <TableRow
                key={execution.id}
                className="cursor-pointer"
                onClick={() => navigate(paths.executionDetail(execution.id))}
              >
                <TableCell>
                  <Badge variant={STATUS_VARIANT[execution.status]}>{execution.status}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{execution.mode}</TableCell>
                <TableCell className="text-muted-foreground">
                  {execution.startedAt ? new Date(execution.startedAt).toLocaleString() : '—'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDuration(execution.durationMs)}
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(event) => {
                      event.stopPropagation()
                      navigate(paths.workflowEditor(execution.workflowId))
                    }}
                  >
                    Open workflow
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
