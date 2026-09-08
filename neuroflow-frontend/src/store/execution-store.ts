import { create } from 'zustand'
import type { ExecutionEvent } from '@/types/executions'

// Live per-run session state, driven entirely by SSE events -- NOT
// persisted (docs/06-canvas-and-editor.md #6.11/#6.12 rule 3: narrow
// selectors so a node only re-renders for its own status change, not
// every event). Separate from canvas-store: this is "what happened during
// the run currently being watched," not editor/graph state.

export type NodeRunStatus = 'idle' | 'running' | 'success' | 'error' | 'skipped'
export type RunStatus = 'idle' | 'running' | 'success' | 'error' | 'canceled'

export interface NodeRunSummary {
  status: NodeRunStatus
  durationMs?: number
  itemsOut?: number
}

export interface LogLine {
  nodeId?: string
  message: string
  timestamp: string
}

interface ExecutionRunState {
  executionId: string | null
  status: RunStatus
  nodeRuns: Record<string, NodeRunSummary>
  logs: LogLine[]

  startRun: (executionId: string) => void
  applyEvent: (event: ExecutionEvent) => void
  reset: () => void
}

export const useExecutionStore = create<ExecutionRunState>((set) => ({
  executionId: null,
  status: 'idle',
  nodeRuns: {},
  logs: [],

  startRun: (executionId) =>
    set({ executionId, status: 'running', nodeRuns: {}, logs: [] }),

  applyEvent: (event) =>
    set((state) => {
      if (state.executionId !== event.executionId) return state
      switch (event.event) {
        case 'execution.started':
          return { status: 'running' }
        case 'node.started': {
          const nodeId = event.nodeId as string
          return { nodeRuns: { ...state.nodeRuns, [nodeId]: { status: 'running' } } }
        }
        case 'node.finished': {
          const nodeId = event.nodeId as string
          return {
            nodeRuns: {
              ...state.nodeRuns,
              [nodeId]: {
                status: event.status as NodeRunStatus,
                durationMs: event.durationMs as number | undefined,
                itemsOut: event.itemsOut as number | undefined,
              },
            },
          }
        }
        case 'node.log': {
          const line: LogLine = {
            nodeId: event.nodeId as string | undefined,
            message: String(event.message ?? ''),
            timestamp: event.timestamp,
          }
          return { logs: [...state.logs, line] }
        }
        case 'execution.finished':
          return { status: event.status as RunStatus }
        default:
          return state
      }
    }),

  reset: () => set({ executionId: null, status: 'idle', nodeRuns: {}, logs: [] }),
}))

export function useNodeRunStatus(nodeId: string): NodeRunStatus {
  return useExecutionStore((s) => s.nodeRuns[nodeId]?.status ?? 'idle')
}

export function useNodeRunSummary(nodeId: string): NodeRunSummary | undefined {
  return useExecutionStore((s) => s.nodeRuns[nodeId])
}
