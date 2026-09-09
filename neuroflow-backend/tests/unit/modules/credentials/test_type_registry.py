"""Declarative auth injection: `apply_authentication` builds request kwargs
from a credential's decrypted data without the caller ever handling the
raw value directly. See docs/15-security-and-credentials.md #15.6 item 3
and docs/13-node-catalog-and-sdk.md #13.6.
"""

from __future__ import annotations

from app.modules.credentials.type_registry import (
    AuthenticationSpec,
    apply_authentication,
    get_credential_type,
    list_credential_types,
    render_credential_template,
)


def test_three_built_in_types_are_registered() -> None:
    keys = {t.key for t in list_credential_types()}

    assert keys == {"httpHeaderAuth", "httpBasicAuth", "oauth2Generic"}


def test_unknown_type_returns_none() -> None:
    assert get_credential_type("doesNotExist") is None


def test_render_credential_template_substitutes_placeholders() -> None:
    result = render_credential_template(
        "={{ $credentials.headerValue }}", {"headerValue": "Bearer abc123"}
    )

    assert result == "Bearer abc123"


def test_render_credential_template_missing_field_becomes_empty_string() -> None:
    result = render_credential_template("{{ $credentials.missing }}", {})

    assert result == ""


def test_generic_auth_injects_a_templated_header() -> None:
    spec = AuthenticationSpec(
        type="generic",
        properties={"headers": {"Authorization": "=Bearer {{ $credentials.token }}"}},
    )

    kwargs = apply_authentication(spec, {"token": "sk-abc"}, {})

    assert kwargs["headers"]["Authorization"] == "Bearer sk-abc"


def test_generic_auth_can_template_the_header_name_too() -> None:
    descriptor = get_credential_type("httpHeaderAuth")
    assert descriptor is not None
    spec = descriptor.authenticate

    kwargs = apply_authentication(
        spec, {"headerName": "X-Api-Key", "headerValue": "secret-value"}, {}
    )

    assert kwargs["headers"] == {"X-Api-Key": "secret-value"}


def test_basic_auth_base64_encodes_username_and_password() -> None:
    import base64

    descriptor = get_credential_type("httpBasicAuth")
    assert descriptor is not None
    spec = descriptor.authenticate

    kwargs = apply_authentication(
        spec, {"username": "alice", "password": "wonderland"}, {}
    )

    expected = "Basic " + base64.b64encode(b"alice:wonderland").decode()
    assert kwargs["headers"]["Authorization"] == expected


def test_apply_authentication_preserves_existing_kwargs() -> None:
    spec = AuthenticationSpec(
        type="generic",
        properties={"headers": {"Authorization": "={{ $credentials.t }}"}},
    )

    kwargs = apply_authentication(spec, {"t": "x"}, {"timeout": 5.0, "json": {"a": 1}})

    assert kwargs["timeout"] == 5.0
    assert kwargs["json"] == {"a": 1}
    assert kwargs["headers"]["Authorization"] == "x"
