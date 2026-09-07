import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Check, Copy, Plus, Trash2, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
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
import { ROLES, type Role } from '@/types/auth'
import type { Invitation } from '@/types/organizations'
import {
  useInviteMember,
  useMembers,
  useRemoveMember,
  useUpdateMemberRole,
} from '@/endpoints/organizations'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'

const INVITABLE_ROLES = ROLES.filter((role) => role !== 'owner')

const inviteSchema = z.object({
  email: z.string().min(1, 'Email is required.').email('Enter a valid email address.'),
  role: z.enum(INVITABLE_ROLES as [Role, ...Role[]]),
})
type InviteFormValues = z.infer<typeof inviteSchema>

function roleLabel(role: Role): string {
  return role[0]!.toUpperCase() + role.slice(1)
}

function InviteMemberDialog({
  organizationId,
  open,
  onOpenChange,
}: {
  organizationId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [issued, setIssued] = useState<Invitation | null>(null)
  const [copied, setCopied] = useState(false)
  const inviteMember = useInviteMember(organizationId)

  const {
    register,
    handleSubmit,
    reset,
    setError,
    control,
    formState: { errors },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { role: 'member' },
  })

  const close = () => {
    onOpenChange(false)
    setIssued(null)
    setCopied(false)
    reset()
  }

  const onSubmit = handleSubmit(async (values) => {
    try {
      const invitation = await inviteMember.mutateAsync(values)
      setIssued(invitation)
    } catch (error) {
      setError('root', {
        message: isApiError(error) ? error.message : 'Something went wrong. Try again.',
      })
    }
  })

  const inviteLink = issued ? `${window.location.origin}/invitations/${issued.token}/accept` : ''

  const copyLink = async () => {
    await navigator.clipboard.writeText(inviteLink)
    setCopied(true)
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        {issued ? (
          <>
            <DialogHeader>
              <DialogTitle>Invitation created</DialogTitle>
              <DialogDescription>
                There&apos;s no email delivery yet -- copy this link and send it to{' '}
                {issued.email} yourself. It expires in 7 days.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2">
              <Input readOnly value={inviteLink} onFocus={(e) => e.target.select()} />
              <Button type="button" size="icon" variant="outline" onClick={copyLink}>
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
                <span className="sr-only">Copy link</span>
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
              <DialogTitle>Invite a member</DialogTitle>
              <DialogDescription>They'll join with the role you choose below.</DialogDescription>
            </DialogHeader>
            <form onSubmit={onSubmit}>
              <FieldGroup>
                <Field data-invalid={Boolean(errors.email)}>
                  <FieldLabel htmlFor="invite-email">Email</FieldLabel>
                  <Input
                    id="invite-email"
                    type="email"
                    placeholder="colleague@company.com"
                    autoFocus
                    {...register('email')}
                  />
                  <FieldError errors={errors.email ? [errors.email] : undefined} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="invite-role">Role</FieldLabel>
                  <Controller
                    control={control}
                    name="role"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger id="invite-role" className="w-full">
                          <SelectValue placeholder="Role" />
                        </SelectTrigger>
                        <SelectContent>
                          {INVITABLE_ROLES.map((role) => (
                            <SelectItem key={role} value={role}>
                              {roleLabel(role)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </Field>
                {errors.root && (
                  <p role="alert" className="text-sm text-destructive">
                    {errors.root.message}
                  </p>
                )}
              </FieldGroup>
              <DialogFooter>
                <Button type="submit" disabled={inviteMember.isPending}>
                  {inviteMember.isPending ? 'Sending...' : 'Send invitation'}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function MemberRoleCell({
  organizationId,
  userId,
  role,
  canManage,
  isSelf,
}: {
  organizationId: string
  userId: string
  role: Role
  canManage: boolean
  isSelf: boolean
}) {
  const updateRole = useUpdateMemberRole(organizationId)

  // Owners aren't reassignable from this control -- demoting the org's
  // last owner is rejected server-side anyway (there is no UI signal for
  // "which one is the last one", so the row stays read-only for owners
  // entirely rather than failing unpredictably on submit).
  if (!canManage || role === 'owner') {
    return <Badge variant="outline">{roleLabel(role)}</Badge>
  }

  return (
    <Select
      value={role}
      onValueChange={(value) => updateRole.mutate({ userId, role: value as Role })}
    >
      <SelectTrigger size="sm" disabled={isSelf || updateRole.isPending}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {INVITABLE_ROLES.map((r) => (
          <SelectItem key={r} value={r}>
            {roleLabel(r)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export default function MembersPage() {
  const currentOrganization = useCurrentOrganization()
  const [inviteOpen, setInviteOpen] = useState(false)

  if (!currentOrganization) {
    return (
      <ComingSoon icon={Users} title="Members" description="Join or create an organization first." />
    )
  }

  return (
    <MembersPageContent
      organizationId={currentOrganization.id}
      canManage={currentOrganization.role === 'owner' || currentOrganization.role === 'admin'}
      inviteOpen={inviteOpen}
      setInviteOpen={setInviteOpen}
    />
  )
}

function MembersPageContent({
  organizationId,
  canManage,
  inviteOpen,
  setInviteOpen,
}: {
  organizationId: string
  canManage: boolean
  inviteOpen: boolean
  setInviteOpen: (open: boolean) => void
}) {
  const { data: members, isLoading } = useMembers(organizationId)
  const removeMember = useRemoveMember(organizationId)

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Members</CardTitle>
            <CardDescription>Who has access to this organization.</CardDescription>
          </div>
          {canManage && (
            <Button size="sm" onClick={() => setInviteOpen(true)}>
              <Plus className="size-4" />
              Invite
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  {canManage && <TableHead className="w-10" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members?.map((member) => (
                  <TableRow key={member.userId}>
                    <TableCell>{member.name}</TableCell>
                    <TableCell className="text-muted-foreground">{member.email}</TableCell>
                    <TableCell>
                      <MemberRoleCell
                        organizationId={organizationId}
                        userId={member.userId}
                        role={member.role}
                        canManage={canManage}
                        isSelf={false}
                      />
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        {member.role !== 'owner' && (
                          <Button
                            size="icon-sm"
                            variant="ghost"
                            onClick={() => removeMember.mutate(member.userId)}
                            disabled={removeMember.isPending}
                          >
                            <Trash2 className="size-4" />
                            <span className="sr-only">Remove {member.name}</span>
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <InviteMemberDialog
        organizationId={organizationId}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
      />
    </>
  )
}
