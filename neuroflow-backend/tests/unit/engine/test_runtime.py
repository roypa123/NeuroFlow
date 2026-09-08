"""Retry policy and per-node `onError` handling. See
docs/12-execution-engine.md #12.4: only idempotent-declared nodes are
retried automatically, and `onError` controls whether a failure stops the
execution or is emitted as data."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from app.core.object_storage import NullObjectStorage
from app.engine.context import ExecutionContext
from app.engine.dag import DagNode
from app.engine.runtime import run_node
from app.modules.nodes.base import (
    BaseNode,
    ExecutionInfo,
    NodeExecutionContext,
    NodeOutput,
    WorkflowInfo,
)
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor, PortSpec
from app.modules.nodes.registry import NodeRegistry
from app.modules.workflows.schemas import GraphNode, Position


class _FlakyNode(BaseNode):
    """Fails `fail_times` times (a class-level counter, reset per test)
    then succeeds -- lets a test assert exactly how many attempts ran."""

    attempts = 0
    fail_times = 0
    descriptor = NodeTypeDescriptor(
        key="test.flaky",
        name="Flaky",
        group="action",
        category="Test",
        description="d",
        icon="circle",
        color="cat-app",
        idempotent=True,
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
    )

    async def execute(self, _ctx: NodeExecutionContext) -> NodeOutput:
        type(self).attempts += 1
        if type(self).attempts <= type(self).fail_times:
            raise RuntimeError("transient failure")
        return {"main": [[Item(json={"ok": True})]]}


class _AlwaysFailsNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="test.alwaysFails",
        name="AlwaysFails",
        group="action",
        category="Test",
        description="d",
        icon="circle",
        color="cat-app",
        idempotent=False,
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
    )
    attempts = 0

    async def execute(self, _ctx: NodeExecutionContext) -> NodeOutput:
        type(self).attempts += 1
        raise RuntimeError("permanent failure")


class _FakeNodeExecRow:
    def __init__(self) -> None:
        self.id = uuid4()
        self.started_at = datetime.now(UTC)


class _FakeNodeExecRepo:
    async def create(self, **_kwargs: Any) -> _FakeNodeExecRow:
        return _FakeNodeExecRow()

    async def finish(self, _row: _FakeNodeExecRow, **_kwargs: Any) -> None:
        return None


class _FakeDataRepo:
    async def create_inline(self, **_kwargs: Any) -> Any:
        class _Row:
            id = uuid4()

        return _Row()


@pytest.fixture
def registry() -> NodeRegistry:
    reg = NodeRegistry()
    reg.register(_FlakyNode)
    reg.register(_AlwaysFailsNode)
    return reg


@pytest.fixture
def ctx(registry: NodeRegistry) -> ExecutionContext:
    return ExecutionContext(
        workflow_info=WorkflowInfo(id="w1", name="WF", active=False),
        execution_info=ExecutionInfo(id="e1", mode="manual"),
        registry=registry,
        http_client=None,  # type: ignore[arg-type]
    )


def _dag_node(node_type: str, **overrides: Any) -> DagNode:
    graph_node = GraphNode(
        id="n1", type=node_type, position=Position(x=0, y=0), **overrides
    )
    is_flaky = node_type == "test.flaky"
    descriptor = _FlakyNode.descriptor if is_flaky else _AlwaysFailsNode.descriptor
    return DagNode(node=graph_node, descriptor=descriptor)


async def _run(dag_node: DagNode, ctx: ExecutionContext) -> Any:
    return await run_node(
        dag_node,
        [],
        ctx,
        execution_id=uuid4(),
        node_exec_repo=_FakeNodeExecRepo(),  # type: ignore[arg-type]
        data_repo=_FakeDataRepo(),  # type: ignore[arg-type]
        storage=NullObjectStorage(),
    )


async def test_idempotent_node_is_retried_until_it_succeeds(
    ctx: ExecutionContext,
) -> None:
    _FlakyNode.attempts = 0
    _FlakyNode.fail_times = 2
    dag_node = _dag_node("test.flaky", max_tries=3)

    result = await _run(dag_node, ctx)

    assert result.status == "success"
    assert _FlakyNode.attempts == 3


async def test_idempotent_node_gives_up_after_max_tries(ctx: ExecutionContext) -> None:
    _FlakyNode.attempts = 0
    _FlakyNode.fail_times = 10
    dag_node = _dag_node("test.flaky", max_tries=3)

    result = await _run(dag_node, ctx)

    assert result.status == "error"
    assert _FlakyNode.attempts == 3


async def test_non_idempotent_node_is_never_retried(ctx: ExecutionContext) -> None:
    _AlwaysFailsNode.attempts = 0
    dag_node = _dag_node("test.alwaysFails", max_tries=5)

    result = await _run(dag_node, ctx)

    assert result.status == "error"
    assert _AlwaysFailsNode.attempts == 1


async def test_on_error_continue_emits_error_item_instead_of_failing(
    ctx: ExecutionContext,
) -> None:
    _AlwaysFailsNode.attempts = 0
    dag_node = _dag_node("test.alwaysFails", on_error="continue")

    result = await _run(dag_node, ctx)

    assert result.status == "error"
    assert result.outputs.get("main")
    assert result.outputs["main"][0].json_["error"]["message"] == "permanent failure"
