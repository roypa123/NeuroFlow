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

Phase 5 adds `credentials: dict[str, CredentialBinding]` (pre-decrypted by
`app.engine` immediately before the node runs, never by the node itself --
see docs/15-security-and-credentials.md #15.6) and `ExecutionSuspended`,
the exception a Wait/approval node raises to suspend rather than finish
(docs/12-execution-engine.md #12.5). Both stay here rather than in
`app.engine` for the same reason `NodeExecutionContext` does: a real node
implementation in `app/nodes/` needs to construct/raise them without
importing the engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from app.core.http_client import AsyncHttpClient
from app.modules.credentials.type_registry import (
    AuthenticationSpec,
    apply_authentication,
)
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor

if TYPE_CHECKING:
    import httpx

NodeOutput = dict[str, list[list[Item]]]


class ExecutionSuspended(Exception):  # noqa: N818 - matches docs' name exactly
    """Raised by a node (e.g. Wait) to suspend the execution rather than
    fail or complete it. See docs/12-execution-engine.md #12.5.

    Lives on the node SDK, not `app.engine`, so both a node implementation
    (`app.nodes.wait`) and the engine (`app.engine.runtime`, which catches
    it) can import it without either depending on the other's package --
    the same "shared SDK type" role `NodeExecutionContext` already plays.
    """

    def __init__(
        self, *, resume_token: str, resume_after: datetime | None = None
    ) -> None:
        super().__init__("Execution suspended")
        self.resume_token = resume_token
        self.resume_after = resume_after


@dataclass(slots=True, frozen=True)
class CredentialBinding:
    """A node's requested credential, pre-decrypted and paired with its
    type's `AuthenticationSpec` by the engine before the node runs -- a
    node never sees this construction, only `ctx.authenticated_request`'s
    result. See docs/15-security-and-credentials.md #15.6 item 3."""

    data: dict[str, Any]
    authenticate: AuthenticationSpec


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
        credentials: dict[str, CredentialBinding] | None = None,
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

    async def authenticated_request(
        self, requirement: str, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Applies the named credential requirement's `AuthenticationSpec`
        to the request kwargs, then delegates to `ctx.http` -- the node
        never sees the decrypted credential value itself. See docs/15-
        security-and-credentials.md #15.6 item 3."""
        if self.http is None:
            raise RuntimeError("No HTTP client bound to this execution context")
        binding = self.credentials.get(requirement)
        if binding is not None:
            kwargs = apply_authentication(binding.authenticate, binding.data, kwargs)
        return await self.http.request(method, url, **kwargs)

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))


class BaseNode(ABC):
    descriptor: ClassVar[NodeTypeDescriptor]

    @abstractmethod
    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput: ...
