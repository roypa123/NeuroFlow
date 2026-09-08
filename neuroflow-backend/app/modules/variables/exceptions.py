"""Variable-specific errors. See docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class VariableNotFoundError(NotFoundError):
    code = "variable.not_found"


class VariableKeyConflictError(ConflictError):
    code = "variable.key_conflict"


class InvalidVariableKeyError(ValidationError):
    code = "variable.invalid_key"
