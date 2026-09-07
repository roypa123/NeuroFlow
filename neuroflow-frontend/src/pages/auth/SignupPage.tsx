import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError, FieldDescription } from '@/components/ui/field'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'
import { useRegister } from '@/endpoints/auth'
import { useAuth } from '@/context/AuthProvider'
import { isApiError } from '@/api'
import { paths } from '@/routing/paths'

const schema = z.object({
  name: z.string().min(1, 'Name is required.'),
  email: z.string().min(1, 'Email is required.').email('Enter a valid email address.'),
  // Matches the server-side minimum in docs/15-security-and-credentials.md #15.2.
  password: z.string().min(12, 'Use at least 12 characters.'),
})
type FormValues = z.infer<typeof schema>

export default function SignupPage() {
  const navigate = useNavigate()
  const { onAuthenticated } = useAuth()
  const registerMutation = useRegister()

  const {
    register: registerField,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async (values) => {
    try {
      const result = await registerMutation.mutateAsync(values)
      onAuthenticated(result.accessToken, result.user)
      navigate(paths.home(), { replace: true })
    } catch (error) {
      if (isApiError(error) && error.code === 'auth.email_taken') {
        setError('email', { message: 'An account with this email already exists.' })
        return
      }
      setError('root', {
        message: isApiError(error) ? error.message : 'Something went wrong. Try again.',
      })
    }
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create your account</CardTitle>
          <CardDescription>Start building workflows in a few seconds.</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit} noValidate>
          <CardContent>
            <FieldGroup>
              <Field data-invalid={Boolean(errors.name)}>
                <FieldLabel htmlFor="name">Name</FieldLabel>
                <Input id="name" autoComplete="name" placeholder="Ada Lovelace" {...registerField('name')} />
                <FieldError errors={errors.name ? [errors.name] : undefined} />
              </Field>
              <Field data-invalid={Boolean(errors.email)}>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  {...registerField('email')}
                />
                <FieldError errors={errors.email ? [errors.email] : undefined} />
              </Field>
              <Field data-invalid={Boolean(errors.password)}>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input id="password" type="password" autoComplete="new-password" {...registerField('password')} />
                <FieldDescription>At least 12 characters.</FieldDescription>
                <FieldError errors={errors.password ? [errors.password] : undefined} />
              </Field>
              {errors.root && (
                <p role="alert" className="text-sm text-destructive">
                  {errors.root.message}
                </p>
              )}
            </FieldGroup>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
              {registerMutation.isPending ? 'Creating account...' : 'Create account'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link to={paths.login()} className="font-medium text-foreground underline underline-offset-4">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
