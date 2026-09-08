"""Credential type descriptors -- the credential-side analogue of
`app.modules.nodes.descriptors.NodeTypeDescriptor`. Pure data, safe for the
API to import and serve directly (no secret material, no engine coupling).
See docs/13-node-catalog-and-sdk.md #13.6.

Three built-in types prove the mechanism end to end (declarative header
auth, HTTP basic auth, and a generic OAuth2 authorization-code flow).
Vendor-specific types (Slack, Google, Stripe, ...) are Phase 6/7 catalog
work, not this phase -- see this phase's plan Scope decisions.
"""
from __future__ import annotations

import base64
import re
from typing import Any, Literal

from pydantic import Field

from app.core.schema import CamelModel
from app.modules.nodes.descriptors import NodeProperty

_PLACEHOLDER = re.compile(r"\{\{\s*\$credentials\.(\w+)\s*\}\}")


class AuthenticationSpec(CamelModel):
    """How a credential's decrypted data is applied to an outbound request.
    Declarative so a node never touches the raw value -- see docs/15-
    security-and-credentials.md #15.6 item 3.

    `type="generic"`: `properties` maps a request part ("headers", "qs") to
    a dict of key/value pairs, each of which may contain
    `{{ $credentials.FIELD }}` placeholders -- resolved by
    `app.modules.nodes.base.apply_authentication` at request time. This is
    deliberately a small placeholder substitution, not the full expression
    parser (the same "convenience layer, not a parser port" call already
    made for the frontend's live-expression preview in Phase 4).

    `type="basic"`: `properties` names which two credential fields hold the
    username/password to base64-encode into an `Authorization: Basic ...`
    header -- HTTP basic auth isn't expressible as plain string templating.
    """

    type: Literal["generic", "basic"] = "generic"
    properties: dict[str, dict[str, str]] = Field(default_factory=dict)


class CredentialTestSpec(CamelModel):
    method: str = "GET"
    url: str  # may contain {{ $credentials.FIELD }} placeholders


class OAuth2Spec(CamelModel):
    """Marks a type as OAuth2-capable. For `oauth2Generic` the actual
    authorize/token URLs live on the credential's own stored properties
    (filled in when the credential is created) rather than here, since a
    generic type has no fixed provider -- see `CredentialService.
    start_oauth`/`complete_oauth`."""

    scope: str = ""


class CredentialTypeDescriptor(CamelModel):
    key: str
    name: str
    properties: list[NodeProperty] = Field(default_factory=list)
    authenticate: AuthenticationSpec
    test: CredentialTestSpec | None = None
    oauth: OAuth2Spec | None = None


_HTTP_HEADER_AUTH = CredentialTypeDescriptor(
    key="httpHeaderAuth",
    name="Header Auth",
    properties=[
        NodeProperty(
            name="headerName",
            display_name="Header Name",
            type="string",
            default="Authorization",
            required=True,
        ),
        NodeProperty(
            name="headerValue",
            display_name="Header Value",
            type="string",
            required=True,
            description="Stored encrypted. Never shown again after saving.",
        ),
    ],
    authenticate=AuthenticationSpec(
        type="generic",
        properties={
            "headers": {"{{ $credentials.headerName }}": "{{ $credentials.headerValue }}"}
        },
    ),
)

_HTTP_BASIC_AUTH = CredentialTypeDescriptor(
    key="httpBasicAuth",
    name="Basic Auth",
    properties=[
        NodeProperty(name="username", display_name="Username", type="string", required=True),
        NodeProperty(
            name="password", display_name="Password", type="string", required=True
        ),
    ],
    authenticate=AuthenticationSpec(
        type="basic",
        properties={"usernameField": {"field": "username"}, "passwordField": {"field": "password"}},
    ),
)

_OAUTH2_GENERIC = CredentialTypeDescriptor(
    key="oauth2Generic",
    name="OAuth2 (Generic)",
    properties=[
        NodeProperty(
            name="authorizationUrl", display_name="Authorization URL", type="string", required=True
        ),
        NodeProperty(name="tokenUrl", display_name="Token URL", type="string", required=True),
        NodeProperty(name="clientId", display_name="Client ID", type="string", required=True),
        NodeProperty(
            name="clientSecret", display_name="Client Secret", type="string", required=True
        ),
        NodeProperty(name="scope", display_name="Scope", type="string", default=""),
    ],
    authenticate=AuthenticationSpec(
        type="generic",
        properties={"headers": {"Authorization": "=Bearer {{ $credentials.accessToken }}"}},
    ),
    oauth=OAuth2Spec(),
)

_BUILTIN_TYPES: dict[str, CredentialTypeDescriptor] = {
    d.key: d for d in (_HTTP_HEADER_AUTH, _HTTP_BASIC_AUTH, _OAUTH2_GENERIC)
}


def list_credential_types() -> list[CredentialTypeDescriptor]:
    return list(_BUILTIN_TYPES.values())


def get_credential_type(key: str) -> CredentialTypeDescriptor | None:
    return _BUILTIN_TYPES.get(key)


def render_credential_template(template: str, data: dict[str, Any]) -> str:
    """Resolves `{{ $credentials.FIELD }}` placeholders against a
    credential's decrypted data. Deliberately a small regex substitution,
    not the full expression parser -- see `AuthenticationSpec`'s docstring.
    A leading `=` (this app's "this is an expression" marker, docs/12-
    execution-engine.md #12.6) is stripped if present so both forms work."""
    text = template[1:] if template.startswith("=") else template
    return _PLACEHOLDER.sub(lambda m: str(data.get(m.group(1), "")), text)


def apply_authentication(
    spec: AuthenticationSpec, data: dict[str, Any], request_kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Injects a credential's decrypted data into outbound request kwargs
    (httpx-shaped: `headers`, `params`, ...) per its `AuthenticationSpec`.
    The caller (a node, via `NodeExecutionContext.authenticated_request`)
    never sees `data` itself -- see docs/15-security-and-credentials.md
    #15.6 item 3."""
    kwargs = dict(request_kwargs)
    if spec.type == "basic":
        username_field = spec.properties.get("usernameField", {}).get("field", "username")
        password_field = spec.properties.get("passwordField", {}).get("field", "password")
        pair = f"{data.get(username_field, '')}:{data.get(password_field, '')}"
        token = base64.b64encode(pair.encode()).decode()
        headers = dict(kwargs.get("headers") or {})
        headers["Authorization"] = f"Basic {token}"
        kwargs["headers"] = headers
        return kwargs

    for part, pairs in spec.properties.items():
        target = dict(kwargs.get(part) or {})
        for raw_key, raw_value in pairs.items():
            target[render_credential_template(raw_key, data)] = render_credential_template(
                raw_value, data
            )
        kwargs[part] = target
    return kwargs
