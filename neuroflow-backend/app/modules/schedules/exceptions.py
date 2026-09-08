"""Schedule-specific errors. See docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ValidationError


class InvalidCronExpressionError(ValidationError):
    code = "schedule.invalid_cron"
