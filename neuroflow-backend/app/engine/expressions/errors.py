"""Expression errors carry the offending expression and (optionally) the
resolved scope, so a failure is diagnosable from the UI alone -- see
docs/12-execution-engine.md #12.6: "an expression failure is a node error
with the offending expression and the resolved scope attached."
"""
from __future__ import annotations

from typing import Any


class ExpressionError(Exception):
    def __init__(
        self, message: str, *, expression: str, scope: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.expression = expression
        self.scope = scope or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "expression": self.expression,
            "scope": self.scope,
        }
