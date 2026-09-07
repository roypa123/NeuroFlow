import * as React from "react"

const MOBILE_BREAKPOINT = 768

// useSyncExternalStore rather than a state+effect pair: this is exactly the
// "subscribe to a browser API, read its current value" case it exists for,
// and it sidesteps the extra render an effect-driven setState would cause.
function subscribe(onChange: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

function getSnapshot() {
  return window.innerWidth < MOBILE_BREAKPOINT
}

export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot)
}
