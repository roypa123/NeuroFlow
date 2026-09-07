import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router'
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
import { useForgotPassword } from '@/endpoints/auth'
import { paths } from '@/routing/paths'

const schema = z.object({
  email: z.string().min(1, 'Email is required.').email('Enter a valid email address.'),
})
type FormValues = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const forgotPassword = useForgotPassword()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit(async (values) => {
    await forgotPassword.mutateAsync(values.email)
    // Always show the same confirmation, whether or not the email exists --
    // docs/15-security-and-credentials.md #15.2.
    setSubmitted(true)
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Reset your password</CardTitle>
          <CardDescription>
            {submitted
              ? "If an account exists for that email, we've sent a reset link."
              : "Enter your email and we'll send you a reset link."}
          </CardDescription>
        </CardHeader>
        {!submitted && (
          <form onSubmit={onSubmit} noValidate>
            <CardContent>
              <FieldGroup>
                <Field data-invalid={Boolean(errors.email)}>
                  <FieldLabel htmlFor="email">Email</FieldLabel>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    {...register('email')}
                  />
                  <FieldError errors={errors.email ? [errors.email] : undefined} />
                </Field>
              </FieldGroup>
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button type="submit" className="w-full" disabled={forgotPassword.isPending}>
                {forgotPassword.isPending ? 'Sending...' : 'Send reset link'}
              </Button>
            </CardFooter>
          </form>
        )}
        <CardFooter className="justify-center pt-0">
          <Link to={paths.login()} className="text-sm font-medium underline underline-offset-4">
            Back to sign in
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
