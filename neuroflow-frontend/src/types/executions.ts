import { z } from 'zod'
import { workflowGraphSchema } from './workflows'

// Mirrors app/modules/executions/schemas.py -- docs/11-api-design.md #11.8.

export const executionStatusSchema = z.enum([
  'queued',
  'running',
  'success',
  'error',
  'canceled',
  'waiting',
])
export type ExecutionStatus = z.infer<typeof executionStatusSchema>

export const executionModeSchema = z.enum([
  'manual',
  'trigger',
  'webhook',
  'schedule',
  'retry',
  'sub',
])
export type ExecutionMode = z.infer<typeof executionModeSchema>

export const nodeExecutionStatusSchema = z.enum(['running', 'success', 'error', 'skipped'])
export type NodeExecutionStatus = z.infer<typeof nodeExecutionStatusSchema>

export const executionSummarySchema = z.object({
  id: z.string(),
  workflowId: z.string(),
  workflowVersionId: z.string(),
  projectId: z.string(),
  status: executionStatusSchema,
  mode: executionModeSchema,
  startedAt: z.string().nullable(),
  finishedAt: z.string().nullable(),
  durationMs: z.number().nullable(),
  createdAt: z.string(),
})
export type ExecutionSummary = z.infer<typeof executionSummarySchema>

export const executionErrorSchema = z.object({
  nodeId: z.string().optional(),
  nodeName: z.string().optional(),
  message: z.string(),
  code: z.string().optional(),
  expression: z.string().optional(),
  scope: z.record(z.string(), z.unknown()).optional(),
  errors: z.array(z.string()).optional(),
})
export type ExecutionError = z.infer<typeof executionErrorSchema>

export const nodeExecutionReadSchema = z.object({
  id: z.string(),
  nodeId: z.string(),
  nodeName: z.string(),
  nodeType: z.string(),
  status: nodeExecutionStatusSchema,
  runIndex: z.number(),
  itemsIn: z.number().nullable(),
  itemsOut: z.number().nullable(),
  error: executionErrorSchema.nullable(),
  startedAt: z.string(),
  finishedAt: z.string().nullable(),
  durationMs: z.number().nullable(),
})
export type NodeExecutionRead = z.infer<typeof nodeExecutionReadSchema>

export const executionReadSchema = executionSummarySchema.extend({
  triggerData: z.record(z.string(), z.unknown()).nullable(),
  error: executionErrorSchema.nullable(),
  parentExecutionId: z.string().nullable(),
  retryOfExecutionId: z.string().nullable(),
  graph: workflowGraphSchema,
  nodes: z.array(nodeExecutionReadSchema),
})
export type ExecutionRead = z.infer<typeof executionReadSchema>

export const itemReadSchema = z.object({
  json: z.record(z.string(), z.unknown()),
})
export type ItemRead = z.infer<typeof itemReadSchema>

export const nodeDataReadSchema = z.object({
  inputItems: z.array(itemReadSchema),
  outputItems: z.array(itemReadSchema),
  truncated: z.boolean(),
})
export type NodeDataRead = z.infer<typeof nodeDataReadSchema>

export const executionStatsSchema = z.object({
  byStatus: z.record(z.string(), z.number()),
  total: z.number(),
})
export type ExecutionStats = z.infer<typeof executionStatsSchema>

// SSE payloads -- docs/12-execution-engine.md #12.10. `sequence` is what
// lets a reconnecting client detect a gap and refetch instead of silently
// rendering an incomplete run.
export interface ExecutionEvent {
  event: string
  sequence: number
  executionId: string
  timestamp: string
  [key: string]: unknown
}
