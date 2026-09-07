import { useState } from 'react'
import { Controller, type Control, type ControllerRenderProps } from 'react-hook-form'
import { Braces } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import type { NodeProperty } from '@/types/node-types'
import { MonacoField } from './MonacoField'

// Generic, descriptor-driven field renderer -- docs/06-canvas-and-editor.md
// #6.9. No node ships bespoke inspector code; every field kind is handled
// exactly once, here.

function isExpression(value: unknown): boolean {
  return typeof value === 'string' && value.startsWith('=')
}

interface FieldRendererProps {
  property: NodeProperty
  control: Control
}

export function FieldRenderer({ property, control }: FieldRendererProps) {
  return (
    <Controller
      name={property.name}
      control={control}
      render={({ field, fieldState }) => (
        <FieldBody property={property} field={field} hasError={Boolean(fieldState.error)} />
      )}
    />
  )
}

interface FieldBodyProps {
  property: NodeProperty
  field: ControllerRenderProps
  hasError: boolean
}

// A real named component (not an inline callback) -- react-hook-form's
// Controller.render is invoked from within Controller's own render pass,
// so hooks are only safe to call here, in a proper function component.
function FieldBody({ property, field, hasError }: FieldBodyProps) {
  const canBeExpression = !property.noDataExpression && property.type !== 'boolean'
  const [fxOn, setFxOn] = useState(isExpression(field.value))

  if (property.type === 'notice') {
    return (
      <p className="rounded-md bg-muted p-2 text-xs text-muted-foreground">
        {property.description}
      </p>
    )
  }
  if (property.type === 'hidden') return null

  if (fxOn && canBeExpression) {
    return (
      <Field data-invalid={hasError}>
        <div className="flex items-center justify-between">
          <FieldLabel>{property.displayName}</FieldLabel>
          <Button
            type="button"
            size="icon-sm"
            variant="ghost"
            onClick={() => setFxOn(false)}
            title="Switch to fixed value"
          >
            <Braces className="size-3.5 text-primary" />
          </Button>
        </div>
        <MonacoField
          value={typeof field.value === 'string' ? field.value.replace(/^=/, '') : ''}
          onChange={(next) => field.onChange(`=${next}`)}
          language="plaintext"
          height={80}
        />
        {property.description && <FieldDescription>{property.description}</FieldDescription>}
      </Field>
    )
  }

  const fxToggle = canBeExpression && (
    <Button
      type="button"
      size="icon-sm"
      variant="ghost"
      onClick={() => setFxOn(true)}
      title="Switch to expression"
    >
      <Braces className="size-3.5 text-muted-foreground" />
    </Button>
  )

  switch (property.type) {
    case 'boolean':
      return (
        <Field orientation="horizontal" data-invalid={hasError}>
          <FieldLabel htmlFor={property.name}>{property.displayName}</FieldLabel>
          <Switch
            id={property.name}
            checked={Boolean(field.value)}
            onCheckedChange={field.onChange}
          />
        </Field>
      )

    case 'options':
      return (
        <Field data-invalid={hasError}>
          <FieldLabel>{property.displayName}</FieldLabel>
          <Select
            value={typeof field.value === 'string' ? field.value : undefined}
            onValueChange={field.onChange}
          >
            <SelectTrigger>
              <SelectValue placeholder={property.placeholder ?? 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {property.options?.map((opt) => (
                <SelectItem key={String(opt.value)} value={String(opt.value)}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )

    case 'multiOptions': {
      const selected: string[] = Array.isArray(field.value) ? field.value : []
      return (
        <Field data-invalid={hasError}>
          <FieldLabel>{property.displayName}</FieldLabel>
          <div className="flex flex-col gap-1.5">
            {property.options?.map((opt) => {
              const value = String(opt.value)
              return (
                <label key={value} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={selected.includes(value)}
                    onCheckedChange={(checked) =>
                      field.onChange(
                        checked ? [...selected, value] : selected.filter((v) => v !== value),
                      )
                    }
                  />
                  {opt.label}
                </label>
              )
            })}
          </div>
        </Field>
      )
    }

    case 'json':
    case 'collection':
      return (
        <Field data-invalid={hasError}>
          <div className="flex items-center justify-between">
            <FieldLabel>{property.displayName}</FieldLabel>
            {fxToggle}
          </div>
          <JsonOrCodeField property={property} field={field} />
          {property.description && <FieldDescription>{property.description}</FieldDescription>}
        </Field>
      )

    case 'code':
      return (
        <Field data-invalid={hasError}>
          <div className="flex items-center justify-between">
            <FieldLabel>{property.displayName}</FieldLabel>
            {fxToggle}
          </div>
          <JsonOrCodeField property={property} field={field} />
          {property.description && <FieldDescription>{property.description}</FieldDescription>}
        </Field>
      )

    case 'number':
      return (
        <Field data-invalid={hasError}>
          <div className="flex items-center justify-between">
            <FieldLabel htmlFor={property.name}>{property.displayName}</FieldLabel>
            {fxToggle}
          </div>
          <Input
            id={property.name}
            type="number"
            value={typeof field.value === 'number' ? field.value : ''}
            onChange={(e) =>
              field.onChange(e.target.value === '' ? null : Number(e.target.value))
            }
            placeholder={property.placeholder ?? undefined}
          />
        </Field>
      )

    case 'dateTime':
      return (
        <Field data-invalid={hasError}>
          <FieldLabel htmlFor={property.name}>{property.displayName}</FieldLabel>
          <Input
            id={property.name}
            type="datetime-local"
            value={typeof field.value === 'string' ? field.value : ''}
            onChange={(e) => field.onChange(e.target.value)}
          />
        </Field>
      )

    case 'color':
      return (
        <Field data-invalid={hasError}>
          <FieldLabel htmlFor={property.name}>{property.displayName}</FieldLabel>
          <Input
            id={property.name}
            type="color"
            value={typeof field.value === 'string' ? field.value : '#000000'}
            onChange={(e) => field.onChange(e.target.value)}
            className="h-9 w-16 p-1"
          />
        </Field>
      )

    case 'credential':
    case 'resourceLocator':
      return (
        <Field>
          <FieldLabel>{property.displayName}</FieldLabel>
          <p className="rounded-md border border-dashed border-border p-2 text-xs text-muted-foreground">
            Not available until credentials ship (Phase 5).
          </p>
        </Field>
      )

    default:
      return (
        <Field data-invalid={hasError}>
          <div className="flex items-center justify-between">
            <FieldLabel htmlFor={property.name}>{property.displayName}</FieldLabel>
            {fxToggle}
          </div>
          <Input
            id={property.name}
            value={typeof field.value === 'string' ? field.value : ''}
            onChange={(e) => field.onChange(e.target.value)}
            placeholder={property.placeholder ?? undefined}
          />
        </Field>
      )
  }
}

function JsonOrCodeField({
  property,
  field,
}: {
  property: NodeProperty
  field: { value: unknown; onChange: (value: unknown) => void }
}) {
  const [text, setText] = useState(() => stringifyValue(field.value))
  const [error, setError] = useState<string | null>(null)
  const language =
    property.type === 'code'
      ? ((property.typeOptions?.editorLanguage as string | undefined) ?? 'python')
      : 'json'

  return (
    <div className="flex flex-col gap-1">
      <MonacoField
        value={text}
        language={language}
        onChange={(next) => {
          setText(next)
          if (property.type === 'code') {
            field.onChange(next)
            setError(null)
            return
          }
          try {
            field.onChange(next.trim() === '' ? {} : JSON.parse(next))
            setError(null)
          } catch {
            setError('Invalid JSON')
          }
        }}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (value === undefined || value === null) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return ''
  }
}
