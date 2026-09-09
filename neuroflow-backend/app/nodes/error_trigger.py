"""Error Trigger -- fires when a workflow named by another workflow's
`settings.errorWorkflowId` fails (UC-6). The failed execution's redacted
error dict is passed as this trigger's input item by
`run_execution.py`'s `ExecutionFailedError` handler, via the same
`create_and_enqueue_system` path webhook/schedule/sub-workflow triggers
already use. See docs/12-execution-engine.md #12.2
(`maybe_trigger_error_workflow`) and this phase's plan, finding #6.
"""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor, PortSpec


class ErrorTriggerNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.errorTrigger",
        version=1,
        name="Error Trigger",
        group="trigger",
        category="Core",
        description="Runs this workflow when a linked workflow fails.",
        icon="octagon-alert",
        color="cat-trigger",
        aliases=["on error", "error workflow"],
        subtitle=None,
        inputs=[],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        items = ctx.input_items or [Item(json={})]
        return {"main": [items]}
