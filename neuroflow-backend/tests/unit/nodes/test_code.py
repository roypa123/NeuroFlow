"""Exercises the real subprocess-based JS sandbox (app/engine/code_sandbox.py)
-- Node is available in this environment, so these are genuine sandbox
invocations, not mocks. See docs/12-execution-engine.md #12.7."""
from __future__ import annotations

import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.code import CodeExecutionError, CodeNode


async def test_identity_expression_returns_input_unchanged() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"a": 1})], params={"code": "items", "mode": "allItems"}
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"a": 1}


async def test_expression_can_transform_items() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"a": 1}), Item(json={"a": 2})],
        params={
            "code": "items.map(i => ({...i, doubled: i.a * 2}))",
            "mode": "allItems",
        },
    )

    result = await node.execute(ctx)

    assert [i.json_["doubled"] for i in result["main"][0]] == [2, 4]


async def test_per_item_mode_runs_once_per_item() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"a": 1}), Item(json={"a": 2})],
        params={"code": "({...item, seen: true})", "mode": "perItem"},
    )

    result = await node.execute(ctx)

    assert [i.json_["a"] for i in result["main"][0]] == [1, 2]
    assert all(i.json_["seen"] for i in result["main"][0])


async def test_require_is_not_available() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[],
        params={"code": "require('fs').readFileSync('/etc/passwd')", "mode": "allItems"},
    )

    with pytest.raises(CodeExecutionError):
        await node.execute(ctx)


async def test_non_object_result_is_rejected() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(input_items=[], params={"code": "42", "mode": "allItems"})

    with pytest.raises(CodeExecutionError):
        await node.execute(ctx)


async def test_infinite_loop_is_killed_by_the_sandbox_timeout() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[], params={"code": "while(true){}", "mode": "allItems"}
    )

    with pytest.raises(CodeExecutionError):
        await node.execute(ctx)
