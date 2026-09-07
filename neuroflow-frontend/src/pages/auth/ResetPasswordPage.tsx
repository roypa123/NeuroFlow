import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'
import { useResetPassword } from '@/endpoints/auth'
import { isApiError } from '@/api'
import { paths } from '@/routing/paths'

const schema = z.object({
  newPassword: z.string().min(8, 'Password must be at least 8 characters.'),
})
type FormValues = z.infer<typeof schema>

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const [done, setDone] = useState(false)
  const resetPassword = useResetPassword()

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async (values) => {
    try {
      await resetPassword.mutateAsync({ token, ...values })
      setDone(true)
    } catch (error) {
      setError('root', {
        message: isApiError(error)
          ? 'This reset link is invalid or has expired.'
          : 'Something went wrong. Try again.',
      })
    }
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Set a new password</CardTitle>
          <CardDescription>
            {done
              ? 'Your password has been changed. Every other session has been signed out.'
              : 'Choose a new password for your account.'}
          </CardDescription>
        </CardHeader>
        {!done && !token && (
          <CardContent>
            <p className="text-sm text-destructive">
              This link is missing its reset token. Request a new one from the sign-in page.
            </p>
          </CardContent>
        )}
        {!done && token && (
          <form onSubmit={onSubmit} noValidate>
            <CardContent>
              <FieldGroup>
                <Field data-invalid={Boolean(errors.newPassword)}>
                  <FieldLabel htmlFor="new-password">New password</FieldLabel>
                  <Input
                    id="new-password"
                    type="password"
                    autoComplete="new-password"
                    {...register('newPassword')}
                  />
                  <FieldError errors={errors.newPassword ? [errors.newPassword] : undefined} />
                </Field>
                {errors.root && (
                  <p role="alert" className="text-sm text-destructive">
                    {errors.root.message}
                  </p>
                )}
              </FieldGroup>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={resetPassword.isPending}>
                {resetPassword.isPending ? 'Saving...' : 'Save new password'}
              </Button>
            </CardFooter>
          </form>
        )}
        {done && (
          <CardFooter>
            <Button className="w-full" onClick={() => navigate(paths.login())}>
              Continue to sign in
            </Button>
          </CardFooter>
        )}
        {!done && (
          <CardFooter className="justify-center pt-0">
            <Link to={paths.login()} className="text-sm font-medium underline underline-offset-4">
              Back to sign in
            </Link>
          </CardFooter>
        )}
      </Card>
    </div>
  )
}
