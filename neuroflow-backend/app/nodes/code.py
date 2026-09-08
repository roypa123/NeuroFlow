"""Code -- run a JavaScript snippet against the input items. See
docs/12-execution-engine.md #12.7 and docs/13-node-catalog-and-sdk.md #13.5.

Phase 3 shipped this node against a restricted Python `eval()` as an
explicitly documented placeholder, since no engine existed yet to invoke
`execute()` at all. Phase 4 replaces that with the real design: a
subprocess-isolated JavaScript sandbox (`app/engine/code_sandbox.py`). No
version bump -- the Phase 3 placeholder never executed in production (there
was no engine to call it), so there is no stored-graph compatibility
concern to preserve.
"""
from __future__ import annotations

from app.engine.code_sandbox import CodeSandboxError, run_code
from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
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
        description="Run a JavaScript snippet against the input items.",
        icon="code",
        color="cat-code",
        aliases=["javascript", "js", "script", "function"],
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=False,
        properties=[
            NodeProperty(
                name="mode",
                display_name="Mode",
                type="options",
                default="allItems",
                options=[
                    PropertyOption(label="Run Once for All Items", value="allItems"),
                    PropertyOption(label="Run Once per Item", value="perItem"),
                ],
            ),
            NodeProperty(
                name="code",
                display_name="Code",
                type="code",
                required=True,
                default="items",
                description=(
                    "JavaScript. In 'Run Once for All Items' mode, `items` is an "
                    "array of the input item JSON and the snippet's value becomes "
                    "the output. In 'Run Once per Item' mode, `item` is a single "
                    "item's JSON. The result must be an object or an array of "
                    "objects."
                ),
                type_options={"editorLanguage": "javascript", "rows": 10},
                no_data_expression=True,
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        code = ctx.params["code"]
        mode = ctx.params.get("mode", "allItems")
        items = [item.json_ for item in ctx.input_items]
        try:
            result = await run_code(code, items=items, mode=mode)
        except CodeSandboxError as exc:
            raise CodeExecutionError(str(exc)) from exc

        if mode == "perItem":
            if not isinstance(result, list):
                raise CodeExecutionError("Per-item mode must produce one result per item")
            rows = result
        else:
            rows = [result] if isinstance(result, dict) else result

        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise CodeExecutionError("Code must return an object or an array of objects")
        return {"main": [[Item(json=row) for row in rows]]}
