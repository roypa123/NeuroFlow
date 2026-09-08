"""Reachability-aware scheduling -- the branch-skip cascade in particular
(docs/12-execution-engine.md #12.3). Uses lightweight fake repositories
instead of a real database: this is exercising `execute_dag`'s own
control-flow logic, not persistence, and testcontainers-backed Postgres
isn't reachable in this sandbox anyway (see tests/conftest.py)."""
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
from app.engine.scheduler import execute_dag
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


class _FakeDataRow:
    def __init__(self) -> None:
        self.id = uuid4()


class _FakeDataRepo:
    async def create_inline(self, **_kwargs: Any) -> _FakeDataRow:
        return _FakeDataRow()

    async def create_object_reference(self, **_kwargs: Any) -> _FakeDataRow:
        return _FakeDataRow()

    async def get(self, _data_id: UUID) -> None:
        return None


class _FakeRedis:
    async def get(self, _key: str) -> None:
        return None

    async def publish(self, _channel: str, _message: str) -> None:
        return None


@pytest.fixture
def engine_ctx() -> ExecutionContext:
    return ExecutionContext(
        workflow_info=WorkflowInfo(id="w1", name="WF", active=False),
        execution_info=ExecutionInfo(id="e1", mode="manual"),
        registry=build_runtime_registry(),
        http_client=None,  # type: ignore[arg-type]  # unused by these nodes
    )


def node(node_id: str, node_type: str, x: float = 0, **params: Any) -> GraphNode:
    return GraphNode(
        id=node_id, type=node_type, position=Position(x=x, y=0), parameters=params
    )


def edge(
    edge_id: str, source: str, target: str, source_handle: str | None = None
) -> GraphEdge:
    return GraphEdge(
        id=edge_id, source=source, target=target, source_handle=source_handle
    )


async def _run(graph: WorkflowGraph, engine_ctx: ExecutionContext) -> _FakeNodeExecRepo:
    registry = engine_ctx.registry
    dag = DAG.from_graph(graph, registry)
    node_exec_repo = _FakeNodeExecRepo()
    execution_id = uuid4()
    publisher = EventPublisher(_FakeRedis(), execution_id)  # type: ignore[arg-type]
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
    return node_exec_repo


async def test_taking_the_true_branch_skips_the_false_only_successor(
    engine_ctx: ExecutionContext,
) -> None:
    graph = WorkflowGraph(
        nodes=[
            node("t", "neuroflow.manualTrigger"),
            node("i", "neuroflow.if", 200, value1="a", value2="a", operator="equals"),
            node("true_branch", "neuroflow.noOp", 400),
            node("false_branch", "neuroflow.noOp", 400),
        ],
        edges=[
            edge("e1", "t", "i"),
            edge("e2", "i", "true_branch", source_handle="true"),
            edge("e3", "i", "false_branch", source_handle="false"),
        ],
    )
    node_exec_repo = await _run(graph, engine_ctx)
    statuses = {kwargs["status"] for kwargs in node_exec_repo.finished}
    # true_branch really ran (recorded via node_exec_repo.finish), while
    # false_branch was never even started -- it's cascaded-skipped inside
    # the scheduler and never reaches run_node/node_exec_repo at all.
    assert "success" in statuses
    ran_node_count = len(node_exec_repo.finished)
    assert ran_node_count == 3  # trigger, if, true_branch -- not false_branch


async def test_a_node_fed_only_by_a_dead_branch_is_skipped_and_cascades(
    engine_ctx: ExecutionContext,
) -> None:
    graph = WorkflowGraph(
        nodes=[
            node("t", "neuroflow.manualTrigger"),
            node("i", "neuroflow.if", 200, value1="a", value2="a", operator="equals"),
            node("false_branch", "neuroflow.noOp", 400),
            node("downstream", "neuroflow.noOp", 600),
        ],
        edges=[
            edge("e1", "t", "i"),
            edge("e2", "i", "false_branch", source_handle="false"),
            edge("e3", "false_branch", "downstream"),
        ],
    )
    node_exec_repo = await _run(graph, engine_ctx)
    # "a" == "a" takes the true branch; false_branch is never run, and
    # downstream (fed only by false_branch) is cascade-skipped without
    # ever reaching run_node/node_exec_repo either.
    assert len(node_exec_repo.finished) == 2  # trigger, if only
