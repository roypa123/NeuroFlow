import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  /** Rendered in place of children on error. Defaults to a generic panel. */
  fallback?: (reset: () => void) => ReactNode
}

interface State {
  error: Error | null
}

// Wraps each route element and the canvas separately (once it exists), so a
// crash in one does not blank the whole shell -- see
// docs/04-frontend-architecture.md #4.8.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console -- no telemetry sink wired yet (Phase 8)
    console.error('Unhandled render error', error, info.componentStack)
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback(this.reset)
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-6 text-center">
          <div>
            <h2 className="text-lg font-semibold">Something went wrong</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {this.state.error.message || 'An unexpected error occurred.'}
            </p>
          </div>
          <Button onClick={this.reset}>Try again</Button>
        </div>
      )
    }
    return this.props.children
  }
}
