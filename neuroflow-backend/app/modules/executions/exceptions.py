"""Execution-specific errors. See docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError


class ExecutionNotFoundError(NotFoundError):
    """Also raised for a real execution the caller's org can't see -- see
    docs/17-testing-strategy.md #17.4: cross-tenant access 404s, never
    403s."""

    code = "execution.not_found"


class ExecutionNotCancelableError(ConflictError):
    code = "execution.not_cancelable"


class ExecutionNotRetryableError(ConflictError):
    code = "execution.not_retryable"


class ExecutionNotResumableError(ConflictError):
    code = "execution.not_resumable"
