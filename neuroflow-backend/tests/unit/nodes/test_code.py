from __future__ import annotations

import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.code import CodeExecutionError, CodeNode


async def test_identity_expression_returns_input_unchanged() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"a": 1})], params={"code": "items"}
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"a": 1}


async def test_expression_can_transform_items() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"a": 1}), Item(json={"a": 2})],
        params={"code": "[{**i, 'doubled': i['a'] * 2} for i in items]"},
    )

    result = await node.execute(ctx)

    assert [i.json_["doubled"] for i in result["main"][0]] == [2, 4]


async def test_builtins_are_not_available() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(input_items=[], params={"code": "open('/etc/passwd')"})

    with pytest.raises(CodeExecutionError):
        await node.execute(ctx)


async def test_non_list_or_dict_result_is_rejected() -> None:
    node = CodeNode()
    ctx = NodeExecutionContext(input_items=[], params={"code": "42"})

    with pytest.raises(CodeExecutionError):
        await node.execute(ctx)
