import { z } from 'zod'

// Mirrors app/modules/nodes/descriptors.py -- docs/13-node-catalog-and-sdk.md #13.2.
// Cached with staleTime: Infinity client-side (docs/11-api-design.md #11.9);
// the frontend contains zero per-node code, so every field the canvas/
// inspector needs must come from here.

export const propertyTypeSchema = z.enum([
  'string',
  'number',
  'boolean',
  'options',
  'multiOptions',
  'json',
  'code',
  'credential',
  'collection',
  'resourceLocator',
  'dateTime',
  'color',
  'notice',
  'hidden',
])
export type PropertyType = z.infer<typeof propertyTypeSchema>

export const nodeGroupSchema = z.enum(['trigger', 'action', 'flow', 'ai', 'data'])
export type NodeGroup = z.infer<typeof nodeGroupSchema>

export const portSpecSchema = z.object({
  type: z.string(),
  label: z.string().nullable(),
})
export type PortSpec = z.infer<typeof portSpecSchema>

export const propertyOptionSchema = z.object({
  label: z.string(),
  value: z.unknown(),
})

export const displayOptionsSchema = z.object({
  show: z.record(z.string(), z.array(z.unknown())).nullable(),
  hide: z.record(z.string(), z.array(z.unknown())).nullable(),
})
export type DisplayOptions = z.infer<typeof displayOptionsSchema>

export const nodePropertySchema = z.object({
  name: z.string(),
  displayName: z.string(),
  type: propertyTypeSchema,
  default: z.unknown(),
  required: z.boolean(),
  description: z.string().nullable(),
  placeholder: z.string().nullable(),
  options: z.array(propertyOptionSchema).nullable(),
  loadOptionsMethod: z.string().nullable(),
  displayOptions: displayOptionsSchema.nullable(),
  typeOptions: z.record(z.string(), z.unknown()).nullable(),
  noDataExpression: z.boolean(),
})
export type NodeProperty = z.infer<typeof nodePropertySchema>

export const nodeTypeDescriptorSchema = z.object({
  key: z.string(),
  version: z.number(),
  name: z.string(),
  group: nodeGroupSchema,
  category: z.string(),
  description: z.string(),
  icon: z.string(),
  color: z.string(),
  aliases: z.array(z.string()),
  subtitle: z.string().nullable(),
  documentationUrl: z.string().nullable(),
  inputs: z.array(portSpecSchema),
  outputs: z.array(portSpecSchema),
  properties: z.array(nodePropertySchema),
  idempotent: z.boolean(),
  supportsErrorOutput: z.boolean(),
  maxItems: z.number().nullable(),
})
export type NodeTypeDescriptor = z.infer<typeof nodeTypeDescriptorSchema>
