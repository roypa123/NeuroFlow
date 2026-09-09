"""Multi-input-port routing -- `target_handle` (already modeled on
`GraphEdge`, previously unused by the scheduler) keeps a node's two
declared input ports (e.g. Merge's "Input 1"/"Input 2") from being
flattened together. See this phase's plan, finding #2. Uses the same
fake-repository harness as `tests/unit/engine/test_scheduler.py`, running
the real `neuroflow.merge` node through the real `execute_dag`."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.object_storage import NullObjectStorage
from app.engine.context import ExecutionContext
from app.engine.dag import DAG
from app.engine.events import EventPublisher
from app.engine.registry import build_runtime_registry
from app.engine.scheduler import execute_dag
from app.modules.nodes.base import ExecutionInfo, WorkflowInfo
from app.modules.workflows.schemas import GraphEdge, GraphNode, Position, WorkflowGraph


class _FakeNodeExecRow:
    def __init__(self) -> None:
        from datetime import UTC, datetime

        self.id = uuid4()
        self.started_at = datetime.now(UTC)


class _FakeNodeExecRepo:
    async def create(self, **_kwargs: Any) -> _FakeNodeExecRow:
        return _FakeNodeExecRow()

    async def finish(self, _row: _FakeNodeExecRow, **_kwargs: Any) -> None:
        return None


class _FakeDataRow:
    def __init__(self) -> None:
        self.id = uuid4()


class _FakeDataRepo:
    async def create_inline(self, **_kwargs: Any) -> _FakeDataRow:
        return _FakeDataRow()

    async def create_object_reference(self, **_kwargs: Any) -> _FakeDataRow:
        return _FakeDataRow()


class _FakeRedis:
    async def get(self, _key: str) -> None:
        return None

    async def publish(self, _channel: str, _message: str) -> None:
        return None


def _node(node_id: str, node_type: str, x: float = 0, **params: Any) -> GraphNode:
    return GraphNode(
        id=node_id, type=node_type, position=Position(x=x, y=0), parameters=params
    )


def _edge(
    edge_id: str,
    source: str,
    target: str,
    *,
    source_handle: str | None = None,
    target_handle: str | None = None,
) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        source_handle=source_handle,
        target_handle=target_handle,
    )


async def test_merge_keeps_branches_separate_regardless_of_completion_order() -> None:
    engine_ctx = ExecutionContext(
        workflow_info=WorkflowInfo(id="w1", name="WF", active=False),
        execution_info=ExecutionInfo(id="e1", mode="manual"),
        registry=build_runtime_registry(),
        http_client=None,  # type: ignore[arg-type]
    )
    graph = WorkflowGraph(
        nodes=[
            _node("t", "neuroflow.manualTrigger"),
            _node("a", "neuroflow.set", 200, mode="keepOnlySet", fields={"x": 1}),
            _node("b", "neuroflow.set", 200, mode="keepOnlySet", fields={"y": 2}),
            _node("m", "neuroflow.merge", 400, mode="append"),
        ],
        edges=[
            _edge("e1", "t", "a"),
            _edge("e2", "t", "b"),
            _edge("e3", "a", "m", target_handle="Input 1"),
            _edge("e4", "b", "m", target_handle="Input 2"),
        ],
    )
    dag = DAG.from_graph(graph, engine_ctx.registry)
    execution_id = uuid4()
    publisher = EventPublisher(_FakeRedis(), execution_id)  # type: ignore[arg-type]

    await execute_dag(
        dag,
        engine_ctx,
        execution_id=execution_id,
        node_exec_repo=_FakeNodeExecRepo(),  # type: ignore[arg-type]
        data_repo=_FakeDataRepo(),  # type: ignore[arg-type]
        storage=NullObjectStorage(),
        redis=_FakeRedis(),  # type: ignore[arg-type]
        publisher=publisher,
        trigger_items=[],
    )

    # Merge (mode=append) always emits Input 1's items before Input 2's,
    # regardless of which branch's Set node happened to finish first in
    # the scheduler's parallel batch -- the grouping is by `target_handle`,
    # not completion order.
    assert engine_ctx.node_outputs["m"] == [{"x": 1}, {"y": 2}]
