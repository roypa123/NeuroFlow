"""Project-specific errors. Subclass the shared AppError hierarchy -- see
docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.core.exceptions import PermissionError as AppPermissionError


class ProjectNotFoundError(NotFoundError):
    """Also raised for a real project the caller's org can't see -- see
    docs/17-testing-strategy.md #17.4: cross-tenant access 404s, never
    403s."""

    code = "project.not_found"


class CannotDeletePersonalProjectError(AppPermissionError):
    code = "project.cannot_delete_personal"
