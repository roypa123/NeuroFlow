import { defineConfig, devices } from '@playwright/test'

// E2E config per docs/17-testing-strategy.md #17.9: thirty tests maximum,
// against a full stack, no waitForTimeout. Test files land under e2e/ as
// real user journeys are implemented (Phase 3+) -- this file exists now so
// the harness is ready and reviewable before the first spec is written.
//
// Note: this sandbox has no network path to Playwright's browser-binary
// CDN, so `npx playwright install` cannot complete here. The React Flow
// risk spike (src/spike/) was verified via Vitest + jsdom instead --
// see docs/02-current-state-audit.md #2.3.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
