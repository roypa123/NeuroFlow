"""The node SDK base class. Importable by the API (it declares an
interface, no node logic), and subclassed by the real implementations in
`app/nodes/`, which the API must never import -- see
docs/03-system-architecture.md #3.9.

`NodeExecutionContext` is intentionally minimal in Phase 3: no engine
exists yet to invoke `execute()` at all, so this only needs to be shaped
correctly for unit tests and for Phase 4 to build on. Per-item expression
resolution, the SSRF-guarded HTTP client, and object storage are engine
runtime concerns from docs/12-execution-engine.md and land in Phase 4 --
`params_for_item` returning the same resolved `params` for every item is
the deliberate placeholder for that.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.modules.nodes.descriptors import Item, NodeTypeDescriptor

NodeOutput = dict[str, list[list[Item]]]


class NodeExecutionContext:
    def __init__(
        self, *, input_items: list[Item], params: dict[str, Any]
    ) -> None:
        self.input_items = input_items
        self.params = params
        self.logs: list[tuple[str, str]] = []

    def params_for_item(self, index: int) -> dict[str, Any]:  # noqa: ARG002
        return self.params

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))


class BaseNode(ABC):
    descriptor: ClassVar[NodeTypeDescriptor]

    @abstractmethod
    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput: ...
