import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router'
import { CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { useAcceptInvitation } from '@/endpoints/organizations'
import { useWorkspaceStore } from '@/store/workspace-store'
import { isApiError } from '@/api'
import { paths } from '@/routing/paths'

// Reached from an invite link an admin shares by hand (there's no email
// delivery yet -- see MembersPage's InviteMemberDialog). Requires being
// signed in: RequireAuth in routes.tsx bounces an unauthenticated visitor
// to /login first, and LoginPage's `state.from` redirect brings them right
// back here to actually accept once they've signed in.
export default function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const setCurrentOrganizationId = useWorkspaceStore((s) => s.setCurrentOrganizationId)
  const acceptInvitation = useAcceptInvitation()
  const attempted = useRef(false)

  useEffect(() => {
    if (!token || attempted.current) return
    attempted.current = true
    acceptInvitation.mutate(token, {
      onSuccess: (result) => setCurrentOrganizationId(result.organizationId),
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fire once per token
  }, [token])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-sm">
        {acceptInvitation.isIdle || acceptInvitation.isPending ? (
          <CardHeader className="items-center text-center">
            <Spinner className="size-8" />
            <CardTitle className="mt-2">Joining organization...</CardTitle>
          </CardHeader>
        ) : acceptInvitation.isSuccess ? (
          <>
            <CardHeader className="items-center text-center">
              <CheckCircle2 className="size-10 text-primary" />
              <CardTitle className="mt-2">You&apos;re in</CardTitle>
              <CardDescription>You&apos;ve joined the organization.</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button className="w-full" onClick={() => navigate(paths.workflows())}>
                Continue
              </Button>
            </CardFooter>
          </>
        ) : (
          <>
            <CardHeader className="items-center text-center">
              <XCircle className="size-10 text-destructive" />
              <CardTitle className="mt-2">Invitation not valid</CardTitle>
              <CardDescription>
                {isApiError(acceptInvitation.error)
                  ? acceptInvitation.error.message
                  : 'This invitation link is invalid or has expired.'}
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button className="w-full" variant="outline" onClick={() => navigate(paths.home())}>
                Go to NeuroFlow
              </Button>
            </CardFooter>
          </>
        )}
      </Card>
    </div>
  )
}
