"""Workflow-specific errors. See docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class WorkflowNotFoundError(NotFoundError):
    """Also raised for a real workflow the caller's org can't see -- see
    docs/17-testing-strategy.md #17.4: cross-tenant access 404s, never
    403s."""

    code = "workflow.not_found"


class WorkflowVersionNotFoundError(NotFoundError):
    code = "workflow.version_not_found"


class WorkflowVersionConflictError(ConflictError):
    """Raised when a PATCH's baseVersionId doesn't match the current latest
    version -- see docs/11-api-design.md #11.7."""

    code = "workflow.version_conflict"


class WorkflowValidationError(ValidationError):
    code = "workflow.invalid_graph"
