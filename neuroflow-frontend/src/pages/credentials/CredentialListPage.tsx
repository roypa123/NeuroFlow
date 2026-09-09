import { useState } from 'react'
import { useForm, Controller, type Control } from 'react-hook-form'
import { KeyRound, Plus, Trash2, CheckCircle2, XCircle, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Field, FieldGroup, FieldLabel, FieldError, FieldDescription } from '@/components/ui/field'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ComingSoon } from '@/components/common/ComingSoon'
import { isApiError } from '@/api'
import { useProjects } from '@/endpoints/projects'
import {
  useCreateCredential,
  useCredentials,
  useCredentialTypes,
  useDeleteCredential,
  useStartOAuth,
  useTestCredential,
} from '@/endpoints/credentials'
import type { CredentialTypeDescriptor } from '@/types/credentials'
import type { NodeProperty } from '@/types/node-types'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'
import { paths } from '@/routing/paths'

function CredentialPropertyField({
  property,
  control,
}: {
  property: NodeProperty
  control: Control
}) {
  return (
    <Controller
      name={property.name}
      control={control}
      render={({ field }) => {
        if (property.type === 'boolean') {
          return (
            <Field orientation="horizontal">
              <FieldLabel>{property.displayName}</FieldLabel>
              <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
            </Field>
          )
        }
        if (property.type === 'options') {
          return (
            <Field>
              <FieldLabel>{property.displayName}</FieldLabel>
              <Select
                value={typeof field.value === 'string' ? field.value : ''}
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
        }
        return (
          <Field>
            <FieldLabel>{property.displayName}</FieldLabel>
            <Input
              type={/secret|password|token/i.test(property.name) ? 'password' : 'text'}
              value={typeof field.value === 'string' ? field.value : ''}
              onChange={(e) => field.onChange(e.target.value)}
              placeholder={property.placeholder ?? undefined}
              defaultValue={typeof property.default === 'string' ? property.default : undefined}
            />
            {property.description && <FieldDescription>{property.description}</FieldDescription>}
          </Field>
        )
      }}
    />
  )
}

function CreateCredentialDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { data: types } = useCredentialTypes()
  const [selectedType, setSelectedType] = useState<CredentialTypeDescriptor | null>(null)
  const createCredential = useCreateCredential()

  const {
    register,
    handleSubmit,
    reset,
    control,
    setError,
    formState: { errors },
  } = useForm<Record<string, unknown>>({ defaultValues: { name: '' } })

  const close = () => {
    onOpenChange(false)
    reset()
    setSelectedType(null)
  }

  const onSubmit = handleSubmit(async (values) => {
    if (!selectedType) return
    const { name, ...rest } = values
    try {
      await createCredential.mutateAsync({
        projectId,
        name: (typeof name === 'string' && name) || selectedType.name,
        type: selectedType.key,
        data: rest,
      })
      close()
    } catch (error) {
      setError('root', {
        message: isApiError(error) ? error.message : 'Something went wrong. Try again.',
      })
    }
  })

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New credential</DialogTitle>
          <DialogDescription>
            Stored encrypted. Values are never shown again after saving.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit}>
          <FieldGroup>
            <Field>
              <FieldLabel>Type</FieldLabel>
              <Select
                value={selectedType?.key ?? ''}
                onValueChange={(key) => setSelectedType(types?.find((t) => t.key === key) ?? null)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a credential type..." />
                </SelectTrigger>
                <SelectContent>
                  {types?.map((t) => (
                    <SelectItem key={t.key} value={t.key}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            {selectedType && (
              <>
                <Field data-invalid={Boolean(errors.name)}>
                  <FieldLabel htmlFor="cred-name">Name</FieldLabel>
                  <Input
                    id="cred-name"
                    placeholder={selectedType.name}
                    autoFocus
                    {...register('name')}
                  />
                  <FieldError errors={errors.name ? [errors.name] : undefined} />
                </Field>
                {selectedType.properties.map((property) => (
                  <CredentialPropertyField
                    key={property.name}
                    property={property}
                    control={control}
                  />
                ))}
              </>
            )}
            {errors.root && (
              <p role="alert" className="text-sm text-destructive">
                {errors.root.message}
              </p>
            )}
          </FieldGroup>
          <DialogFooter>
            <Button type="submit" disabled={!selectedType || createCredential.isPending}>
              {createCredential.isPending ? 'Creating...' : 'Create credential'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function CredentialListPage() {
  const currentOrganization = useCurrentOrganization()
  if (!currentOrganization) {
    return (
      <ComingSoon
        icon={KeyRound}
        title="Credentials"
        description="Join or create an organization first."
      />
    )
  }
  return <CredentialListPageContent organizationId={currentOrganization.id} />
}

function CredentialListPageContent({ organizationId }: { organizationId: string }) {
  const { data: projects } = useProjects(organizationId)
  const [projectId, setProjectId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const activeProjectId = projectId ?? projects?.[0]?.id ?? null

  const { data: credentials, isLoading } = useCredentials(activeProjectId)
  const deleteCredential = useDeleteCredential()
  const testCredential = useTestCredential()
  const startOAuth = useStartOAuth()
  const [testResults, setTestResults] = useState<Record<string, boolean>>({})

  if (projects && projects.length === 0) {
    return (
      <ComingSoon
        icon={KeyRound}
        title="Credentials"
        description="Create a project first -- every organization starts with a Personal one."
      />
    )
  }

  const handleTest = async (id: string) => {
    const result = await testCredential.mutateAsync(id)
    setTestResults((prev) => ({ ...prev, [id]: result.ok }))
  }

  const handleConnect = async (id: string) => {
    const redirectUri = `${window.location.origin}${paths.credentialOAuthCallback()}`
    const url = await startOAuth.mutateAsync({ id, redirectUri })
    window.open(url, 'neuroflow-oauth', 'width=500,height=650')
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Credentials</h1>
          <p className="text-sm text-muted-foreground">
            Stored encrypted. Used by nodes via declarative auth injection.
          </p>
        </div>
        <div className="flex items-center gap-2">
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
          <Button size="sm" onClick={() => setCreateOpen(true)} disabled={!activeProjectId}>
            <Plus className="size-4" />
            New credential
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : !credentials || credentials.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <KeyRound className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No credentials yet.</p>
          </CardContent>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {credentials.map((credential) => (
              <TableRow key={credential.id}>
                <TableCell className="font-medium">{credential.name}</TableCell>
                <TableCell className="text-muted-foreground">{credential.type}</TableCell>
                <TableCell>
                  {testResults[credential.id] === true && (
                    <Badge variant="default">
                      <CheckCircle2 className="size-3" /> OK
                    </Badge>
                  )}
                  {testResults[credential.id] === false && (
                    <Badge variant="destructive">
                      <XCircle className="size-3" /> Failed
                    </Badge>
                  )}
                  {testResults[credential.id] === undefined && credential.testStatus && (
                    <Badge variant="outline">{credential.testStatus}</Badge>
                  )}
                </TableCell>
                <TableCell className="flex justify-end gap-1">
                  {credential.type === 'oauth2Generic' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleConnect(credential.id)}
                      disabled={startOAuth.isPending}
                    >
                      <Link2 className="size-4" />
                      Connect
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTest(credential.id)}
                    disabled={testCredential.isPending}
                  >
                    Test
                  </Button>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => deleteCredential.mutate(credential.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {activeProjectId && (
        <CreateCredentialDialog
          projectId={activeProjectId}
          open={createOpen}
          onOpenChange={setCreateOpen}
        />
      )}
    </div>
  )
}
