"""A suspended node halts the whole DAG rather than cascading to
successors -- the resume payload isn't known yet. See docs/12-execution-
engine.md #12.5 and this phase's plan finding #5.

Fakes mirror test_scheduler.py's -- exercising execute_dag's control flow,
not persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.object_storage import NullObjectStorage
from app.engine.context import ExecutionContext
from app.engine.dag import DAG
from app.engine.events import EventPublisher
from app.engine.registry import build_runtime_registry
from app.engine.scheduler import ExecutionSuspendedError, execute_dag
from app.modules.nodes.base import ExecutionInfo, WorkflowInfo
from app.modules.workflows.schemas import GraphEdge, GraphNode, Position, WorkflowGraph


class _FakeNodeExecRow:
    def __init__(self) -> None:
        self.id = uuid4()
        self.started_at = datetime.now(UTC)


class _FakeNodeExecRepo:
    def __init__(self) -> None:
        self.finished: list[dict[str, Any]] = []

    async def create(self, **_kwargs: Any) -> _FakeNodeExecRow:
        return _FakeNodeExecRow()

    async def finish(self, _row: _FakeNodeExecRow, **kwargs: Any) -> None:
        self.finished.append(kwargs)


class _FakeDataRepo:
    async def create_inline(self, **_kwargs: Any) -> Any:
        class _Row:
            id = uuid4()

        return _Row()

    async def get(self, _data_id: UUID) -> None:
        return None


class _FakeRedis:
    async def get(self, _key: str) -> None:
        return None

    async def publish(self, _channel: str, _message: str) -> None:
        return None


def node(node_id: str, node_type: str, x: float = 0, **params: Any) -> GraphNode:
    return GraphNode(
        id=node_id, type=node_type, position=Position(x=x, y=0), parameters=params
    )


def edge(edge_id: str, source: str, target: str) -> GraphEdge:
    return GraphEdge(id=edge_id, source=source, target=target)


@pytest.fixture
def engine_ctx() -> ExecutionContext:
    return ExecutionContext(
        workflow_info=WorkflowInfo(id="w1", name="WF", active=False),
        execution_info=ExecutionInfo(id="e1", mode="manual"),
        registry=build_runtime_registry(),
        http_client=None,  # type: ignore[arg-type]
    )


async def test_a_wait_node_suspends_the_execution_before_its_successor_runs(
    engine_ctx: ExecutionContext,
) -> None:
    graph = WorkflowGraph(
        nodes=[
            node("t", "neuroflow.manualTrigger"),
            node("w", "neuroflow.wait", 200, mode="webhook"),
            node("after", "neuroflow.noOp", 400),
        ],
        edges=[edge("e1", "t", "w"), edge("e2", "w", "after")],
    )
    dag = DAG.from_graph(graph, engine_ctx.registry)
    node_exec_repo = _FakeNodeExecRepo()
    execution_id = uuid4()
    publisher = EventPublisher(_FakeRedis(), execution_id)  # type: ignore[arg-type]

    with pytest.raises(ExecutionSuspendedError) as exc_info:
        await execute_dag(
            dag,
            engine_ctx,
            execution_id=execution_id,
            node_exec_repo=node_exec_repo,  # type: ignore[arg-type]
            data_repo=_FakeDataRepo(),  # type: ignore[arg-type]
            storage=NullObjectStorage(),
            redis=_FakeRedis(),  # type: ignore[arg-type]
            publisher=publisher,
            trigger_items=[],
        )

    assert exc_info.value.resume_token
    # Only the trigger and the Wait node itself ran -- "after" never
    # reached run_node, because the DAG halted at the suspension.
    statuses = [kwargs["status"] for kwargs in node_exec_repo.finished]
    assert statuses == ["success", "waiting"]
