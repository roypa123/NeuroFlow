import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { ReactFlowProvider } from '@xyflow/react'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Loader2, Plus, Power, Redo2, Save, Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { isApiError } from '@/api'
import { FlowCanvas } from '@/components/canvas/FlowCanvas'
import { NodePicker } from '@/components/canvas/NodePicker'
import { Inspector } from '@/components/canvas/inspector'
import { useNodeTypesByKey } from '@/endpoints/node-types'
import {
  useActivateWorkflow,
  useDeactivateWorkflow,
  useUpdateWorkflow,
  useWorkflow,
  workflowKeys,
} from '@/endpoints/workflows'
import { fetchWorkflow } from '@/endpoints/workflows/requests'
import { useCanvasStore } from '@/store/canvas-store'
import { useUiStore } from '@/store/ui-store'
import type { VersionConflictDetails } from '@/types/workflows'
import { paths } from '@/routing/paths'

function EditorTopbar({ workflowId }: { workflowId: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: workflow } = useWorkflow(workflowId)
  const nodeTypesByKey = useNodeTypesByKey()
  const updateWorkflow = useUpdateWorkflow(workflowId)
  const activateWorkflow = useActivateWorkflow(workflowId)
  const deactivateWorkflow = useDeactivateWorkflow(workflowId)

  const isDirty = useCanvasStore((s) => s.isDirty)
  const toGraph = useCanvasStore((s) => s.toGraph)
  const baseVersionId = useCanvasStore((s) => s.baseVersionId)
  const markSaved = useCanvasStore((s) => s.markSaved)
  const loadGraph = useCanvasStore((s) => s.loadGraph)
  const undo = useCanvasStore((s) => s.undo)
  const redo = useCanvasStore((s) => s.redo)
  const addNode = useCanvasStore((s) => s.addNode)

  const [name, setName] = useState('')
  const [syncedWorkflowId, setSyncedWorkflowId] = useState<string | null>(null)
  const [conflict, setConflict] = useState<VersionConflictDetails | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Adjusting state during render (not in an effect) when the workflow
  // actually changes -- only resets `name` on a real switch, so a
  // background refetch of the same workflow never clobbers in-progress
  // typing. See https://react.dev/learn/you-might-not-need-an-effect.
  if (workflow && workflow.id !== syncedWorkflowId) {
    setSyncedWorkflowId(workflow.id)
    setName(workflow.name)
  }

  async function save(overrideBaseVersionId?: string) {
    if (!workflow) return
    setSaveError(null)
    try {
      const result = await updateWorkflow.mutateAsync({
        name,
        graph: toGraph(),
        baseVersionId: overrideBaseVersionId ?? baseVersionId ?? undefined,
      })
      queryClient.setQueryData(workflowKeys.detail(workflowId), result)
      markSaved(result.activeVersionId ?? '')
      setConflict(null)
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        const details = error.details
        if (
          details &&
          !Array.isArray(details) &&
          typeof details.actualVersionId === 'string'
        ) {
          setConflict(details as unknown as VersionConflictDetails)
          return
        }
      }
      setSaveError(isApiError(error) ? error.message : 'Failed to save. Try again.')
    }
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        void save()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, baseVersionId, workflow])

  if (!workflow) return null

  return (
    <div className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3">
      <Button size="icon-sm" variant="ghost" onClick={() => navigate(paths.workflows())}>
        <ArrowLeft className="size-4" />
      </Button>
      <Input
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="h-8 max-w-64 border-none px-1 font-medium shadow-none focus-visible:ring-1"
      />
      <span className="text-xs text-muted-foreground">
        {isDirty ? 'Unsaved changes' : 'Saved'}
      </span>
      {saveError && <span className="text-xs text-destructive">{saveError}</span>}
      <div className="flex-1" />
      <Button size="icon-sm" variant="ghost" onClick={() => setPickerOpen(true)} title="Add node (Tab)">
        <Plus className="size-4" />
      </Button>
      <Button size="icon-sm" variant="ghost" onClick={undo} title="Undo (Ctrl/Cmd+Z)">
        <Undo2 className="size-4" />
      </Button>
      <Button size="icon-sm" variant="ghost" onClick={redo} title="Redo (Ctrl/Cmd+Shift+Z)">
        <Redo2 className="size-4" />
      </Button>
      <Button
        size="sm"
        variant={workflow.isActive ? 'default' : 'outline'}
        onClick={() =>
          workflow.isActive ? deactivateWorkflow.mutate() : activateWorkflow.mutate()
        }
        disabled={activateWorkflow.isPending || deactivateWorkflow.isPending}
      >
        <Power className="size-4" />
        {workflow.isActive ? 'Active' : 'Inactive'}
      </Button>
      <Button size="sm" onClick={() => void save()} disabled={updateWorkflow.isPending}>
        {updateWorkflow.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Save className="size-4" />
        )}
        Save
      </Button>

      <NodePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onSelect={(descriptor) => addNode(descriptor, { x: 200, y: 200 })}
      />

      <AlertDialog open={conflict !== null} onOpenChange={(open) => !open && setConflict(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>This workflow was modified by someone else</AlertDialogTitle>
            <AlertDialogDescription>
              Someone else saved a newer version while you were editing. You can reload their
              version (discarding your local changes) or overwrite it with yours.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={async () => {
                const latest = await fetchWorkflow(workflowId)
                queryClient.setQueryData(workflowKeys.detail(workflowId), latest)
                loadGraph(workflowId, latest.activeVersionId, latest.graph, nodeTypesByKey)
                setName(latest.name)
              }}
            >
              Reload theirs
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => conflict && void save(conflict.actualVersionId)}
            >
              Overwrite
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function EditorBody({ workflowId }: { workflowId: string }) {
  const { data: workflow, isLoading } = useWorkflow(workflowId)
  const nodeTypesByKey = useNodeTypesByKey()
  const loadGraph = useCanvasStore((s) => s.loadGraph)
  const loadedForId = useRef<string | null>(null)
  const inspectorWidth = useUiStore((s) => s.inspectorWidth)
  const setInspectorWidth = useUiStore((s) => s.setInspectorWidth)

  useEffect(() => {
    if (!workflow || Object.keys(nodeTypesByKey).length === 0) return
    if (loadedForId.current === workflow.id) return
    loadedForId.current = workflow.id
    loadGraph(workflow.id, workflow.activeVersionId, workflow.graph, nodeTypesByKey)
  }, [workflow, nodeTypesByKey, loadGraph])

  if (isLoading || !workflow) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Loading...
      </div>
    )
  }

  return (
    <ResizablePanelGroup orientation="horizontal" className="flex-1">
      <ResizablePanel minSize="30">
        <FlowCanvas />
      </ResizablePanel>
      <ResizableHandle />
      <ResizablePanel
        defaultSize={inspectorWidth}
        minSize={280}
        maxSize={640}
        onResize={(size) => setInspectorWidth(Math.round(size.inPixels))}
      >
        <Inspector />
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}

export default function WorkflowEditorPage() {
  const { workflowId } = useParams<{ workflowId: string }>()
  if (!workflowId) return null

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <EditorTopbar workflowId={workflowId} />
        <EditorBody workflowId={workflowId} />
      </div>
    </ReactFlowProvider>
  )
}
