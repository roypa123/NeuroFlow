import { useEffect, useState } from 'react'
import { completeOAuth } from '@/endpoints/credentials/requests'

// The OAuth `redirect_uri` points here rather than at the backend --
// completion happens on this page, over the normal API client, instead of
// the backend rendering an HTML confirmation page for an unauthenticated
// browser redirect. See app/modules/credentials/router.py's docstring.

type ParsedCallback = { code: string; state: string } | { error: string }

function parseCallbackParams(): ParsedCallback {
  const params = new URLSearchParams(window.location.search)
  const code = params.get('code')
  const state = params.get('state')
  const errorParam = params.get('error')

  if (errorParam) return { error: `Authorization was denied: ${errorParam}` }
  if (!code || !state) return { error: 'Missing code or state in the callback URL.' }
  return { code, state }
}

export default function OAuthCallbackPage() {
  const [parsed] = useState(parseCallbackParams)
  const [message, setMessage] = useState(
    'error' in parsed ? parsed.error : 'Completing connection...',
  )
  const [failed, setFailed] = useState('error' in parsed)

  useEffect(() => {
    if ('error' in parsed) return

    completeOAuth(parsed.state, parsed.code)
      .then((credential) => {
        setMessage('Connected. You can close this window.')
        window.opener?.postMessage(
          { type: 'neuroflow:oauth-complete', credentialId: credential.id },
          window.location.origin,
        )
        window.close()
      })
      .catch((error: unknown) => {
        const detail =
          error && typeof error === 'object' && 'message' in error
            ? String((error as { message: unknown }).message)
            : 'Connection failed.'
        setFailed(true)
        setMessage(detail)
      })
  }, [parsed])

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-2 p-6 text-center">
      <p className={`text-sm ${failed ? 'text-destructive' : 'text-muted-foreground'}`}>
        {message}
      </p>
    </div>
  )
}
