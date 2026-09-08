"""OAuth2 authorization-code flow helpers -- a manual `httpx` implementation
rather than adding the `authlib` dependency for a single flow, the same
"prefer httpx over a vendor SDK" call Phase 4 made for object storage.

Not run through the SSRF-guarded `AsyncHttpClient`: these calls are made
against a URL the authenticated user themselves configured when creating
the credential (an operator setting up their own integration), not a
value derived from untrusted workflow input -- a different trust boundary
than the HTTP Request node's `ctx.http`, which the SSRF guard in
docs/15-security-and-credentials.md #15.7 exists for.

**Not live-verifiable against a real third-party provider in this sandbox**
(no general outbound internet access here, the same class of gap Phase 4
hit with httpbin.org) -- verified instead against a small local mock
authorization server. See this phase's plan Scope decisions.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

OAUTH_HTTP_TIMEOUT_SECONDS = 15.0


def build_authorization_url(
    *,
    authorization_url: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    separator = "&" if "?" in authorization_url else "?"
    return f"{authorization_url}{separator}{urlencode(params)}"


async def exchange_code_for_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=OAUTH_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
