"""Stop And Error -- deliberately fails the workflow with a user-authored
message. See docs/13-node-catalog-and-sdk.md #13.5. Raises a plain
exception, caught by `app/engine/runtime.py`'s generic node error handler
like every other node failure -- there is no dedicated
`NodeOperationError` base class in this codebase (the §13.8 checklist's
mention of one is aspirational; every existing node just raises a plain
or minimally-subclassed exception, e.g. `app/nodes/code.py`'s
`CodeExecutionError`)."""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import NodeProperty, NodeTypeDescriptor, PortSpec


class WorkflowStoppedError(RuntimeError):
    pass


class StopAndErrorNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.stopAndError",
        version=1,
        name="Stop And Error",
        group="flow",
        category="Core",
        description="Stops the workflow and reports a custom error message.",
        icon="octagon-x",
        color="cat-flow",
        aliases=["throw", "fail", "abort"],
        subtitle="={{ $parameter.message }}",
        inputs=[PortSpec(type="main")],
        outputs=[],
        idempotent=False,
        properties=[
            NodeProperty(
                name="message",
                display_name="Error Message",
                type="string",
                required=True,
                placeholder="Order total exceeds the approval limit",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        raise WorkflowStoppedError(ctx.params.get("message", "Workflow stopped"))
