"""Shared dataclasses passed between `dag.py`, `scheduler.py`, and
`runtime.py`. See docs/12-execution-engine.md #12.3/#12.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.modules.nodes.descriptors import Item

NodeStatus = Literal["success", "error", "skipped", "waiting"]


@dataclass(slots=True)
class NodeResult:
    status: NodeStatus
    outputs: dict[str, list[Item]] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    duration_ms: int = 0
    items_in: int = 0
    items_out: int = 0
    retries: int = 0
    # Set only when status == "waiting" -- see docs/12-execution-engine.md
    # #12.5 and app.modules.nodes.base.ExecutionSuspended.
    resume_token: str | None = None
    resume_after: datetime | None = None
    logs: list[tuple[str, str]] = field(default_factory=list)
