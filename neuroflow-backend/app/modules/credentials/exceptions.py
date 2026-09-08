"""Credential-specific errors. See docs/08-backend-architecture.md #8.5."""

from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class CredentialNotFoundError(NotFoundError):
    """Also raised for a real credential the caller's org can't see -- see
    docs/17-testing-strategy.md #17.4: cross-tenant access 404s, never
    403s."""

    code = "credential.not_found"


class CredentialTypeNotFoundError(NotFoundError):
    code = "credential.type_not_found"


class CredentialInUseError(ConflictError):
    code = "credential.in_use"


class CredentialOAuthError(ValidationError):
    code = "credential.oauth_error"
