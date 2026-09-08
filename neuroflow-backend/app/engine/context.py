"""Per-execution shared runtime state. See docs/12-execution-engine.md
#12.2/#12.12: one `AsyncHttpClient` and one registry are shared across
every node in an execution, not rebuilt per node."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.http_client import AsyncHttpClient
from app.engine.expressions import ExecutionScope, resolve_parameters
from app.engine.expressions.scope import ItemView
from app.modules.nodes.base import ExecutionInfo, WorkflowInfo
from app.modules.nodes.descriptors import Item
from app.modules.nodes.registry import NodeRegistry
from app.modules.workflows.schemas import GraphNode

MAX_PARALLEL_NODES = 5


@dataclass
class ExecutionContext:
    workflow_info: WorkflowInfo
    execution_info: ExecutionInfo
    registry: NodeRegistry
    http_client: AsyncHttpClient
    max_parallel: int = MAX_PARALLEL_NODES
    node_outputs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def scope_for_item(
        self, input_items: list[Item], index: int | None
    ) -> ExecutionScope:
        if index is not None and 0 <= index < len(input_items):
            current_json = input_items[index].json_
        elif input_items:
            current_json = input_items[0].json_
        else:
            current_json = {}
        return ExecutionScope(
            json=current_json,
            binary={},
            items=[ItemView(i.json_) for i in input_items],
            node_outputs=self.node_outputs,
            workflow={
                "id": self.workflow_info.id,
                "name": self.workflow_info.name,
                "active": self.workflow_info.active,
            },
            execution={
                "id": self.execution_info.id,
                "mode": self.execution_info.mode,
                "resumeUrl": self.execution_info.resume_url,
            },
            run_index=0,
            now=datetime.now(UTC),
        )

    def build_resolver(
        self, node: GraphNode, input_items: list[Item]
    ) -> Callable[[int], dict[str, Any]]:
        def resolver(index: int) -> dict[str, Any]:
            scope = self.scope_for_item(input_items, index)
            resolved = resolve_parameters(node.parameters, scope)
            return dict(resolved) if isinstance(resolved, dict) else {}

        return resolver

    def record_node_output(self, node_name: str, items: list[Item]) -> None:
        self.node_outputs[node_name] = [i.json_ for i in items]

    async def aclose(self) -> None:
        await self.http_client.aclose()
