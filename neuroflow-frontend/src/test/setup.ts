import '@testing-library/jest-dom/vitest'

// Required when driving react-dom/client's createRoot directly with
// act() (as the React Flow spike test does), rather than exclusively
// through Testing Library's render(), which sets this itself.
;(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true

// jsdom does not implement ResizeObserver or matchMedia, both of which
// @xyflow/react relies on for viewport measurement. Minimal polyfills so
// component tests involving the canvas don't need per-test boilerplate.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
;(globalThis as any).ResizeObserver = ResizeObserverStub

if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}
