"""Node-type errors. See docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class NodeTypeNotFoundError(NotFoundError):
    code = "node_type.not_found"
