"""Code -- run a snippet against the input items. See
docs/13-node-catalog-and-sdk.md #13.5.

The real sandboxed evaluator is `app/engine`'s job (docs/12-execution-engine.md
#12.7, Phase 4). This is a deliberately restricted placeholder -- `eval()`
with an empty builtins dict and only `items`/`json` exposed -- that proves
the node/descriptor pattern without pretending to be production-safe. As
with the HTTP Request node, nothing invokes `execute()` in production yet:
there is no engine to call it.
"""
from __future__ import annotations

from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


class CodeExecutionError(RuntimeError):
    pass


class CodeNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.code",
        version=1,
        name="Code",
        group="data",
        category="Core",
        description="Run a Python expression against the input items.",
        icon="code",
        color="cat-code",
        aliases=["python", "script", "function"],
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=False,
        properties=[
            NodeProperty(
                name="code",
                display_name="Code",
                type="code",
                required=True,
                default="items",
                description=(
                    "A Python expression whose value becomes the output. `items` "
                    "is a list of dicts (the input item JSON); the expression "
                    "must evaluate to a dict or a list of dicts."
                ),
                type_options={"editorLanguage": "python", "rows": 10},
                no_data_expression=True,
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        code = ctx.params["code"]
        items = [item.json_ for item in ctx.input_items]
        try:
            compiled = compile(code, "<code-node>", "eval")
            result: Any = eval(  # noqa: S307 -- restricted, documented placeholder
                compiled, {"__builtins__": {}}, {"items": items}
            )
        except Exception as exc:  # noqa: BLE001 -- surfaced as a node error, not a crash
            raise CodeExecutionError(str(exc)) from exc

        if isinstance(result, dict):
            result = [result]
        if not isinstance(result, list):
            raise CodeExecutionError("Code must return a dict or a list of dicts")
        return {"main": [[Item(json=row) for row in result]]}
