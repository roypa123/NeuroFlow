import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import {
  Workflow,
  Bot,
  ListChecks,
  KeyRound,
  Settings,
  Sun,
  Moon,
  Monitor,
  LogOut,
  ChevronsUpDown,
  Plus,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuth } from '@/context/AuthProvider'
import { useTheme } from '@/context/ThemeProvider'
import { useCurrentOrganization } from '@/hooks/useCurrentOrganization'
import { useCreateOrganization, useOrganizations } from '@/endpoints/organizations'
import { useWorkspaceStore } from '@/store/workspace-store'
import { paths } from '@/routing/paths'

const NAV_ITEMS = [
  { label: 'Workflows', to: paths.workflows(), icon: Workflow },
  { label: 'Agents', to: paths.agents(), icon: Bot },
  { label: 'Executions', to: paths.executions(), icon: ListChecks },
  { label: 'Credentials', to: paths.credentials(), icon: KeyRound },
] as const

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

function ThemeMenuItems() {
  const { theme, setTheme } = useTheme()
  const options = [
    { value: 'light' as const, label: 'Light', icon: Sun },
    { value: 'dark' as const, label: 'Dark', icon: Moon },
    { value: 'system' as const, label: 'System', icon: Monitor },
  ]
  return (
    <>
      {options.map(({ value, label, icon: Icon }) => (
        <DropdownMenuItem key={value} onClick={() => setTheme(value)} data-active={theme === value}>
          <Icon className="size-4" />
          {label}
        </DropdownMenuItem>
      ))}
    </>
  )
}

function CreateOrganizationDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [name, setName] = useState('')
  const createOrganization = useCreateOrganization()
  const setCurrentOrganizationId = useWorkspaceStore((s) => s.setCurrentOrganizationId)

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    createOrganization.mutate(trimmed, {
      onSuccess: (organization) => {
        setCurrentOrganizationId(organization.id)
        setName('')
        onOpenChange(false)
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create organization</DialogTitle>
          <DialogDescription>
            You&apos;ll be its owner, with a default Personal project.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit}>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="new-org-name">Name</FieldLabel>
              <Input
                id="new-org-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Acme Inc."
                autoFocus
              />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="submit" disabled={!name.trim() || createOrganization.isPending}>
              {createOrganization.isPending ? 'Creating...' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function OrganizationSwitcher() {
  const current = useCurrentOrganization()
  const { data: organizations } = useOrganizations()
  const setCurrentOrganizationId = useWorkspaceStore((s) => s.setCurrentOrganizationId)
  const [createOpen, setCreateOpen] = useState(false)

  // /auth/me already carries the membership list, so the switcher has
  // something correct to render before the separate /organizations query
  // (used here for its own cache/invalidation lifecycle) resolves.
  const list = organizations ?? (current ? [current] : [])

  return (
    <>
      <SidebarMenu>
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger render={<SidebarMenuButton size="lg" />}>
              <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-semibold">
                {current ? current.name[0]?.toUpperCase() : 'N'}
              </div>
              <span className="truncate text-sm font-semibold">
                {current?.name ?? 'NeuroFlow'}
              </span>
              <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent side="bottom" align="start" className="w-56">
              <DropdownMenuLabel>Organizations</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {list.map((org) => (
                <DropdownMenuItem
                  key={org.id}
                  onClick={() => setCurrentOrganizationId(org.id)}
                  data-active={org.id === current?.id}
                >
                  <span className="truncate">{org.name}</span>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setCreateOpen(true)}>
                <Plus className="size-4" />
                Create organization
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
      <CreateOrganizationDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const location = useLocation()

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader>
          <OrganizationSwitcher />
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Workspace</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
                  <SidebarMenuItem key={to}>
                    {/* @base-ui/react uses a `render` prop instead of Radix's
                        asChild -- see docs/02-current-state-audit.md #2.2. */}
                    <SidebarMenuButton
                      render={<Link to={to} />}
                      isActive={location.pathname.startsWith(to)}
                    >
                      <Icon />
                      <span>{label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton render={<Link to={paths.settingsProfile()} />}>
                <Settings />
                <span>Settings</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger render={<SidebarMenuButton size="lg" />}>
                  <Avatar className="size-6">
                    <AvatarFallback>{user ? initials(user.name) : '?'}</AvatarFallback>
                  </Avatar>
                  <span className="truncate">{user?.name ?? 'Loading...'}</span>
                  <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
                </DropdownMenuTrigger>
                <DropdownMenuContent side="top" align="start" className="w-56">
                  <DropdownMenuLabel className="truncate">{user?.email}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <ThemeMenuItems />
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={signOut} variant="destructive">
                    <LogOut className="size-4" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  )
}
