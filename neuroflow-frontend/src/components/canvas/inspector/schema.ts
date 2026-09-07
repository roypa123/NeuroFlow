import { z } from 'zod'
import type { NodeProperty } from '@/types/node-types'

// A resolver derived from the descriptor's properties --
// docs/06-canvas-and-editor.md #6.9. Only `number`/`boolean`/required
// `string` get real typing; every other kind (json, collection, code,
// options, multiOptions, dateTime, color) is intentionally loose -- their
// runtime shape is an object/array/arbitrary string, and the field
// renderer itself is what surfaces "is this valid JSON" style errors.
export function buildParameterSchema(properties: NodeProperty[]) {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const prop of properties) {
    let field: z.ZodTypeAny
    switch (prop.type) {
      case 'number':
        field = z.coerce.number()
        break
      case 'boolean':
        field = z.boolean()
        break
      case 'string':
        field = prop.required
          ? z.string().min(1, `${prop.displayName} is required`)
          : z.string()
        break
      default:
        field = z.any()
    }
    shape[prop.name] = field.optional().nullable()
  }
  return z.object(shape)
}

export function evaluateDisplayOptions(
  displayOptions: {
    show: Record<string, unknown[]> | null
    hide: Record<string, unknown[]> | null
  } | null,
  values: Record<string, unknown>,
): boolean {
  if (!displayOptions) return true
  if (displayOptions.show) {
    for (const [key, allowed] of Object.entries(displayOptions.show)) {
      if (!allowed.includes(values[key])) return false
    }
  }
  if (displayOptions.hide) {
    for (const [key, disallowed] of Object.entries(displayOptions.hide)) {
      if (disallowed.includes(values[key])) return false
    }
  }
  return true
}
