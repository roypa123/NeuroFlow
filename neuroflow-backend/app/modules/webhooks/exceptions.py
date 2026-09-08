"""Webhook-specific errors. See docs/08-backend-architecture.md #8.5."""

from __future__ import annotations

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError


class WebhookNotFoundError(NotFoundError):
    code = "webhook.not_found"


class WebhookAuthError(UnauthorizedError):
    code = "webhook.auth_failed"


class WebhookPathConflictError(ValidationError):
    code = "webhook.path_conflict"
