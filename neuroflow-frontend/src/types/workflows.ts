import { z } from 'zod'

// Mirrors app/modules/workflows/schemas.py -- docs/11-api-design.md #11.7.
// The graph shape matches what @xyflow/react produces so the canvas store
// can send its state straight through -- docs/06-canvas-and-editor.md #6.3.

export const positionSchema = z.object({
  x: z.number(),
  y: z.number(),
})

export const graphNodeSchema = z.object({
  id: z.string(),
  type: z.string(),
  typeVersion: z.number().default(1),
  name: z.string().nullable().default(null),
  position: positionSchema,
  parameters: z.record(z.string(), z.unknown()).default({}),
  // Execution behavior (docs/12-execution-engine.md #12.4) -- additive
  // fields the backend defaults too, so a graph saved before Phase 4
  // round-trips unchanged.
  onError: z.enum(['stop', 'continue', 'continueErrorOutput']).default('stop'),
  maxTries: z.number().default(3),
  waitBetweenTriesMs: z.number().default(1000),
})
export type GraphNode = z.infer<typeof graphNodeSchema>

export const graphEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  sourceHandle: z.string().nullable().default(null),
  targetHandle: z.string().nullable().default(null),
})
export type GraphEdge = z.infer<typeof graphEdgeSchema>

export const viewportSchema = z.object({
  x: z.number().default(0),
  y: z.number().default(0),
  zoom: z.number().default(1),
})

export const workflowGraphSchema = z.object({
  nodes: z.array(graphNodeSchema).default([]),
  edges: z.array(graphEdgeSchema).default([]),
  viewport: viewportSchema.default({ x: 0, y: 0, zoom: 1 }),
})
export type WorkflowGraph = z.infer<typeof workflowGraphSchema>

export const workflowSettingsSchema = z.object({
  timezone: z.string().default('UTC'),
  errorWorkflowId: z.string().nullable().default(null),
  timeoutSeconds: z.number().default(3600),
  maxConcurrency: z.number().default(1),
})
export type WorkflowSettings = z.infer<typeof workflowSettingsSchema>

export const workflowSummarySchema = z.object({
  id: z.string(),
  projectId: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  kind: z.string(),
  isActive: z.boolean(),
  version: z.number(),
  updatedAt: z.string(),
})
export type WorkflowSummary = z.infer<typeof workflowSummarySchema>

export const workflowReadSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  kind: z.string(),
  isActive: z.boolean(),
  activeVersionId: z.string().nullable(),
  version: z.number(),
  settings: workflowSettingsSchema,
  graph: workflowGraphSchema,
  createdAt: z.string(),
  updatedAt: z.string(),
})
export type WorkflowRead = z.infer<typeof workflowReadSchema>

export const workflowVersionReadSchema = z.object({
  id: z.string(),
  version: z.number(),
  checksum: z.string(),
  note: z.string().nullable(),
  createdBy: z.string().nullable(),
  createdAt: z.string(),
})
export type WorkflowVersionRead = z.infer<typeof workflowVersionReadSchema>

export const keysetPageSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    items: z.array(item),
    nextCursor: z.string().nullable(),
    hasMore: z.boolean(),
  })

export interface VersionConflictDetails {
  expectedVersionId: string | null
  actualVersionId: string
}
