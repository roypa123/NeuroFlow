"""Auth-specific errors. Subclass the shared AppError hierarchy -- see
docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError


class EmailAlreadyRegisteredError(ConflictError):
    code = "auth.email_already_registered"


class InvalidCredentialsError(UnauthorizedError):
    code = "auth.invalid_credentials"


class InvalidRefreshTokenError(UnauthorizedError):
    code = "auth.invalid_refresh_token"


class InvalidPasswordResetTokenError(UnauthorizedError):
    code = "auth.invalid_password_reset_token"


class ApiKeyNotFoundError(NotFoundError):
    code = "auth.api_key_not_found"
