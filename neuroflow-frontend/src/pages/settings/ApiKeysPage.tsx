import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Check, Copy, KeyRound, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { ComingSoon } from '@/components/common/ComingSoon'
import { isApiError } from '@/api'
import { AVAILABLE_SCOPES, type ApiKeyCreated } from '@/types/api-keys'
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/endpoints/api-keys'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'

const createSchema = z.object({
  name: z.string().min(1, 'Name is required.'),
  scopes: z.array(z.enum(AVAILABLE_SCOPES)).min(1, 'Pick at least one scope.'),
})
type CreateFormValues = z.infer<typeof createSchema>

function CreateApiKeyDialog({
  organizationId,
  open,
  onOpenChange,
}: {
  organizationId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [issued, setIssued] = useState<ApiKeyCreated | null>(null)
  const [copied, setCopied] = useState(false)
  const createApiKey = useCreateApiKey(organizationId)

  const {
    register,
    handleSubmit,
    reset,
    control,
    setError,
    formState: { errors },
  } = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: '', scopes: [] },
  })

  const close = () => {
    onOpenChange(false)
    setIssued(null)
    setCopied(false)
    reset()
  }

  const onSubmit = handleSubmit(async (values) => {
    try {
      const created = await createApiKey.mutateAsync(values)
      setIssued(created)
    } catch (error) {
      setError('root', {
        message: isApiError(error) ? error.message : 'Something went wrong. Try again.',
      })
    }
  })

  const copyKey = async () => {
    if (!issued) return
    await navigator.clipboard.writeText(issued.key)
    setCopied(true)
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        {issued ? (
          <>
            <DialogHeader>
              <DialogTitle>API key created</DialogTitle>
              <DialogDescription>
                Copy this key now -- it won&apos;t be shown again.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2">
              <Input readOnly value={issued.key} onFocus={(e) => e.target.select()} />
              <Button type="button" size="icon" variant="outline" onClick={copyKey}>
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                <span className="sr-only">Copy key</span>
              </Button>
            </div>
            <DialogFooter>
              <Button type="button" onClick={close}>
                Done
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Create API key</DialogTitle>
              <DialogDescription>
                Choose exactly what this key is allowed to do -- it can never do more than your
                own role allows, and these scopes narrow it further.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={onSubmit}>
              <FieldGroup>
                <Field data-invalid={Boolean(errors.name)}>
                  <FieldLabel htmlFor="key-name">Name</FieldLabel>
                  <Input
                    id="key-name"
                    placeholder="CI pipeline"
                    autoFocus
                    {...register('name')}
                  />
                  <FieldError errors={errors.name ? [errors.name] : undefined} />
                </Field>
                <Field data-invalid={Boolean(errors.scopes)}>
                  <FieldLabel>Scopes</FieldLabel>
                  <Controller
                    control={control}
                    name="scopes"
                    render={({ field }) => (
                      <div className="flex flex-col gap-2">
                        {AVAILABLE_SCOPES.map((scope) => (
                          <label key={scope} className="flex items-center gap-2 text-sm">
                            <Checkbox
                              checked={field.value.includes(scope)}
                              onCheckedChange={(checked) => {
                                field.onChange(
                                  checked
                                    ? [...field.value, scope]
                                    : field.value.filter((s) => s !== scope),
                                )
                              }}
                            />
                            {scope}
                          </label>
                        ))}
                      </div>
                    )}
                  />
                  <FieldError errors={errors.scopes ? [errors.scopes] : undefined} />
                </Field>
                {errors.root && (
                  <p role="alert" className="text-sm text-destructive">
                    {errors.root.message}
                  </p>
                )}
              </FieldGroup>
              <DialogFooter>
                <Button type="submit" disabled={createApiKey.isPending}>
                  {createApiKey.isPending ? 'Creating...' : 'Create key'}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default function ApiKeysPage() {
  const currentOrganization = useCurrentOrganization()
  const [createOpen, setCreateOpen] = useState(false)

  if (!currentOrganization) {
    return (
      <ComingSoon icon={KeyRound} title="API keys" description="Join or create an organization first." />
    )
  }

  const canManage =
    currentOrganization.role === 'owner' || currentOrganization.role === 'admin'

  if (!canManage) {
    return (
      <ComingSoon
        icon={KeyRound}
        title="API keys"
        description="Only owners and admins can manage API keys."
      />
    )
  }

  return (
    <ApiKeysPageContent
      organizationId={currentOrganization.id}
      createOpen={createOpen}
      setCreateOpen={setCreateOpen}
    />
  )
}

function ApiKeysPageContent({
  organizationId,
  createOpen,
  setCreateOpen,
}: {
  organizationId: string
  createOpen: boolean
  setCreateOpen: (open: boolean) => void
}) {
  const { data: keys, isLoading } = useApiKeys(organizationId)
  const revokeApiKey = useRevokeApiKey(organizationId)

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>API keys</CardTitle>
            <CardDescription>Scoped credentials for programmatic access.</CardDescription>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            Create key
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : keys && keys.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Scopes</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell>{key.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {key.prefix}...
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {key.scopes.map((scope) => (
                          <Badge key={scope} variant="outline">
                            {scope}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {key.lastUsedAt ? new Date(key.lastUsedAt).toLocaleString() : 'Never'}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        onClick={() => revokeApiKey.mutate(key.id)}
                        disabled={revokeApiKey.isPending}
                      >
                        <Trash2 className="size-4" />
                        <span className="sr-only">Revoke {key.name}</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No API keys yet.</p>
          )}
        </CardContent>
      </Card>
      <CreateApiKeyDialog
        organizationId={organizationId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </>
  )
}
