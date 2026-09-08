import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Search, Workflow as WorkflowIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ComingSoon } from '@/components/common/ComingSoon'
import { isApiError } from '@/api'
import { useProjects } from '@/endpoints/projects'
import { useCreateWorkflow, useWorkflows } from '@/endpoints/workflows'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'
import { paths } from '@/routing/paths'

const createSchema = z.object({
  name: z.string().min(1, 'Name is required.'),
})
type CreateFormValues = z.infer<typeof createSchema>

function CreateWorkflowDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const createWorkflow = useCreateWorkflow(projectId)
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<CreateFormValues>({ resolver: zodResolver(createSchema) })

  const close = () => {
    onOpenChange(false)
    reset()
  }

  const onSubmit = handleSubmit(async (values) => {
    try {
      const workflow = await createWorkflow.mutateAsync(values)
      close()
      navigate(paths.workflowEditor(workflow.id))
    } catch (error) {
      setError('root', {
        message: isApiError(error) ? error.message : 'Something went wrong. Try again.',
      })
    }
  })

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New workflow</DialogTitle>
          <DialogDescription>You can rename it any time from the editor.</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit}>
          <FieldGroup>
            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="workflow-name">Name</FieldLabel>
              <Input id="workflow-name" placeholder="Stripe -> CRM sync" autoFocus {...register('name')} />
              <FieldError errors={errors.name ? [errors.name] : undefined} />
            </Field>
            {errors.root && (
              <p role="alert" className="text-sm text-destructive">
                {errors.root.message}
              </p>
            )}
          </FieldGroup>
          <DialogFooter>
            <Button type="submit" disabled={createWorkflow.isPending}>
              {createWorkflow.isPending ? 'Creating...' : 'Create workflow'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function WorkflowListPage() {
  const currentOrganization = useCurrentOrganization()

  if (!currentOrganization) {
    return (
      <ComingSoon
        icon={WorkflowIcon}
        title="Workflows"
        description="Join or create an organization first."
      />
    )
  }

  return <WorkflowListPageContent organizationId={currentOrganization.id} />
}

function WorkflowListPageContent({ organizationId }: { organizationId: string }) {
  const { data: projects } = useProjects(organizationId)
  const [projectId, setProjectId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const navigate = useNavigate()

  const activeProjectId = projectId ?? projects?.[0]?.id ?? null
  const { data, isLoading } = useWorkflows(
    activeProjectId ? { projectId: activeProjectId, search } : null,
  )
  const workflows = useMemo(() => data?.pages.flatMap((page) => page.items) ?? [], [data])

  if (projects && projects.length === 0) {
    return (
      <ComingSoon
        icon={WorkflowIcon}
        title="Workflows"
        description="Create a project first -- every organization starts with a Personal one."
      />
    )
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Workflows</h1>
          <p className="text-sm text-muted-foreground">Build, connect, and automate.</p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)} disabled={!activeProjectId}>
          <Plus className="size-4" />
          New workflow
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* '' rather than `undefined` when unset: Base UI's Select fixes
            controlled-vs-uncontrolled from its own first render and never
            revisits it (@base-ui/utils/useControlled) -- if `activeProjectId`
            is still null on that first paint (e.g. before the
            default-to-first-project effect runs), passing `undefined`
            would lock it into uncontrolled mode and it would never show
            the project once one is picked. */}
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
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search workflows..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : workflows.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <WorkflowIcon className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No workflows yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {workflows.map((workflow) => (
            <Card
              key={workflow.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => navigate(paths.workflowEditor(workflow.id))}
            >
              <CardContent className="flex flex-col gap-2 p-4">
                <div className="flex items-center justify-between">
                  <p className="truncate font-medium">{workflow.name}</p>
                  <Badge variant={workflow.isActive ? 'default' : 'outline'}>
                    {workflow.isActive ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  v{workflow.version} - updated {new Date(workflow.updatedAt).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {activeProjectId && (
        <CreateWorkflowDialog
          projectId={activeProjectId}
          open={createOpen}
          onOpenChange={setCreateOpen}
        />
      )}
    </div>
  )
}
