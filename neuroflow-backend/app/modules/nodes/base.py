"""The node SDK base class. Importable by the API (it declares an
interface, no node logic), and subclassed by the real implementations in
`app/nodes/`, which the API must never import -- see
docs/03-system-architecture.md #3.9.

`NodeExecutionContext` grew real fields in Phase 4 (`http`, `workflow`,
`execution`, `run_index`, a per-item expression `resolver`) but stays
importable by the API: `AsyncHttpClient` lives in `app.core.http_client` (a
leaf module, no engine coupling) and `resolver` is just a plain callback
type -- the API only ever imports this class for typing, never constructs
one with a live resolver bound. `app.engine` is what actually builds a
context with a real resolver at runtime (docs/12-execution-engine.md
#12.4). All the new fields default to `None`/empty so every Phase 3 node
unit test that only passes `input_items`/`params` keeps working unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from app.core.http_client import AsyncHttpClient
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor

NodeOutput = dict[str, list[list[Item]]]


@dataclass(slots=True, frozen=True)
class WorkflowInfo:
    id: str
    name: str
    active: bool


@dataclass(slots=True, frozen=True)
class ExecutionInfo:
    id: str
    mode: str
    resume_url: str | None = None


class NodeExecutionContext:
    def __init__(
        self,
        *,
        input_items: list[Item],
        params: dict[str, Any],
        http: AsyncHttpClient | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
        workflow: WorkflowInfo | None = None,
        execution: ExecutionInfo | None = None,
        run_index: int = 0,
        resolver: Callable[[int], dict[str, Any]] | None = None,
    ) -> None:
        self.input_items = input_items
        self.params = params
        self.http = http
        self.credentials = credentials or {}
        self.workflow = workflow
        self.execution = execution
        self.run_index = run_index
        self._resolver = resolver
        self.logs: list[tuple[str, str]] = []

    def params_for_item(self, index: int) -> dict[str, Any]:
        if self._resolver is not None:
            return self._resolver(index)
        return self.params

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))


class BaseNode(ABC):
    descriptor: ClassVar[NodeTypeDescriptor]

    @abstractmethod
    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput: ...
