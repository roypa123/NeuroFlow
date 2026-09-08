"""The `$`-namespace scope objects available inside `{{ }}` expressions.
See docs/12-execution-engine.md #12.6's scope table.

`$vars` and `$env` are deliberately inert in Phase 4: there is no
`variables` module yet (Phase 5), and the environment allow-list is empty
by default -- see this phase's plan's Scope decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.engine.expressions.errors import ExpressionError

_STRFTIME_TOKENS = (
    ("YYYY", "%Y"),
    ("MM", "%m"),
    ("DD", "%d"),
    ("HH", "%H"),
    ("mm", "%M"),
    ("ss", "%S"),
)


class DateTimeView:
    """`$now`/`$today`. `.format()` supports only the common tokens listed
    in `_STRFTIME_TOKENS` -- not a full date-formatting library, since
    nothing in the six Phase 4 nodes needs more than that."""

    def __init__(self, dt: datetime) -> None:
        self._dt = dt

    def format(self, pattern: str) -> str:
        result = pattern
        for token, strftime_code in _STRFTIME_TOKENS:
            result = result.replace(token, strftime_code)
        return self._dt.strftime(result)

    def __str__(self) -> str:
        return self._dt.isoformat()


class ItemView:
    """One item's `.json`/`.binary`, as seen by `$item(i)`/`$items()`."""

    def __init__(self, json_data: dict[str, Any], binary: dict[str, Any] | None = None) -> None:
        self.json = json_data
        self.binary = binary or {}


class NodeAccessor:
    """`$node["Name"]` -- looks up another node's last output by name.
    Raises rather than returning `None` on a miss, since "no node named X
    has run" is exactly the kind of thing that must surface as a
    diagnosable expression error (docs/12-execution-engine.md #12.6)."""

    def __init__(self, outputs_by_name: dict[str, list[dict[str, Any]]]) -> None:
        self._outputs = outputs_by_name

    def __getitem__(self, name: str) -> ItemView:
        items = self._outputs.get(name)
        if not items:
            raise ExpressionError(
                f'No node named "{name}" has produced output yet',
                expression=f'$node["{name}"]',
            )
        return ItemView(items[0])


@dataclass(slots=True)
class ExecutionScope:
    """Everything a single expression evaluation can see. One instance is
    built per (node, item) pair by `app.engine.context`."""

    json: dict[str, Any]
    binary: dict[str, Any]
    items: list[ItemView]
    node_outputs: dict[str, list[dict[str, Any]]]
    workflow: dict[str, Any]
    execution: dict[str, Any]
    run_index: int
    now: datetime
    vars: dict[str, Any] = field(default_factory=dict)
    env: dict[str, Any] = field(default_factory=dict)

    def roots(self) -> dict[str, Any]:
        node_accessor = NodeAccessor(self.node_outputs)
        return {
            "$json": self.json,
            "$binary": self.binary,
            "$item": lambda i: (
                self.items[int(i)] if 0 <= int(i) < len(self.items) else None
            ),
            "$items": lambda: list(self.items),
            "$node": node_accessor,
            "$workflow": self.workflow,
            "$execution": self.execution,
            "$now": DateTimeView(self.now),
            "$today": DateTimeView(self.now),
            "$vars": self.vars,
            "$env": self.env,
            "$runIndex": self.run_index,
        }

    def diagnostic_snapshot(self) -> dict[str, Any]:
        """A JSON-safe-ish summary attached to ExpressionError for the UI --
        deliberately not the full scope (node outputs could be large)."""
        return {
            "json": self.json,
            "runIndex": self.run_index,
            "availableNodes": sorted(self.node_outputs.keys()),
        }
