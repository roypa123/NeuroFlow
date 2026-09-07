import { z } from 'zod'

// Runtime-configurable API base URL (docs/18-deployment-and-operations.md #18.2):
// Vite inlines import.meta.env at BUILD time, which would force every
// self-hosted deployment to rebuild the frontend just to point it at their
// own backend. window.__NEUROFLOW_CONFIG__ is emitted by a small script the
// container writes at start time; the build-time env var is only the local
// dev fallback.
declare global {
  interface Window {
    __NEUROFLOW_CONFIG__?: {
      apiBaseUrl?: string
    }
  }
}

const envSchema = z.object({
  API_BASE_URL: z.string().min(1),
})

function readRuntimeConfig() {
  return typeof window !== 'undefined' ? window.__NEUROFLOW_CONFIG__ : undefined
}

const parsed = envSchema.parse({
  API_BASE_URL:
    readRuntimeConfig()?.apiBaseUrl ??
    import.meta.env.VITE_API_BASE_URL ??
    '/api/v1',
})

export const env = {
  apiBaseUrl: parsed.API_BASE_URL,
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const
