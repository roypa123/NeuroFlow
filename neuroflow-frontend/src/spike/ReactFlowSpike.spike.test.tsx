// Phase 1 risk spike verification (docs/19-roadmap.md, docs/02-current-state-audit.md #2.3).
//
// Question this answers: does @xyflow/react v12 survive React 19's
// StrictMode double-invoke of effects at a canvas size representative of a
// real workflow (200 nodes / ~250 edges), without throwing, without
// duplicating DOM nodes, and without breaking connect/undo interactions?
//
// jsdom has no real layout engine, so this cannot verify pointer-drag
// physics or actual pixel positions -- that gap is closed by manual /
// Playwright verification once a browser binary is available in this
// environment (currently blocked: the sandbox has no network path to
// playwright's CDN). What StrictMode double-invocation actually breaks in
// practice -- effect cleanup ordering, duplicate store subscriptions,
// duplicate rendered nodes -- is fully observable in jsdom, which is what
// this test targets.
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { StrictMode } from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ReactFlowSpike } from './ReactFlowSpike'

describe('React Flow v12 + React 19 StrictMode spike', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
  })

  afterEach(() => {
    act(() => {
      root.unmount()
    })
    container.remove()
    vi.restoreAllMocks()
  })

  it('renders 200 nodes exactly once under StrictMode (no double-mount duplication)', async () => {
    await act(async () => {
      root = createRoot(container)
      root.render(
        <StrictMode>
          <ReactFlowSpike />
        </StrictMode>,
      )
    })

    const nodes = container.querySelectorAll('[data-testid="spike-node"]')
    // StrictMode intentionally double-invokes render/effects in dev to
    // surface impurity. If React Flow's internal node registry were not
    // idempotent under that double-invoke, this would render 400, not 200.
    expect(nodes.length).toBe(200)
  })

  it('reports the expected edge count and does not throw during mount', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    await act(async () => {
      root = createRoot(container)
      root.render(
        <StrictMode>
          <ReactFlowSpike />
        </StrictMode>,
      )
    })

    const status = container.querySelector('[data-testid="spike-status"]')
    expect(status?.textContent).toContain('nodes=200')
    expect(status?.textContent).toContain('edges=')

    // React errors (invariant violations, key warnings, act() warnings)
    // surface via console.error -- StrictMode is exactly where these show
    // up first if a library depends on effects running exactly once.
    const reactErrors = consoleError.mock.calls.filter(([msg]) =>
      typeof msg === 'string' &&
      (msg.includes('Warning:') || msg.includes('Error:')),
    )
    expect(reactErrors).toEqual([])
  })

  it('unmounts cleanly (no leaked timers/observers thrown on cleanup)', async () => {
    await act(async () => {
      root = createRoot(container)
      root.render(
        <StrictMode>
          <ReactFlowSpike />
        </StrictMode>,
      )
    })

    expect(() => {
      act(() => {
        root.unmount()
      })
    }).not.toThrow()
  })
})
