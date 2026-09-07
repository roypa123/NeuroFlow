import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { paths } from '@/routing/paths'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <div>
        <p className="text-sm font-medium text-muted-foreground">404</p>
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist.
        </p>
      </div>
      {/* @base-ui/react uses a `render` prop instead of Radix's asChild --
          see docs/02-current-state-audit.md #2.2. */}
      <Button render={<Link to={paths.home()} />}>Go home</Button>
    </div>
  )
}
