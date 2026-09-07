import type { LucideIcon } from 'lucide-react'

// Placeholder for a page whose real implementation lands in a later phase
// (see docs/19-roadmap.md). Keeps the route table honest -- a route exists
// and renders something real, rather than a blank screen -- without
// pretending the feature is built.
export function ComingSoon({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon
  title: string
  description: string
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-muted">
        <Icon className="size-6 text-muted-foreground" />
      </div>
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
