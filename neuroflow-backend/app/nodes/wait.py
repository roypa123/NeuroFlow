"""Wait -- pauses the execution for a fixed duration, or suspends it until
resumed externally (an approval link, a callback). See docs/12-execution-
engine.md #12.5 and docs/13-node-catalog-and-sdk.md #13.5.

Suspension itself is engine machinery (`app.engine.runtime`/`scheduler`
catch `ExecutionSuspended` and persist `resume_token`/`resume_after`); this
node's whole job is to raise it with the right token/deadline. On resume,
`ExecutionService.resume` marks this node's row `success` directly -- this
`execute()` is never re-entered for the same suspension.
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from app.modules.nodes.base import (
    BaseNode,
    ExecutionSuspended,
    NodeExecutionContext,
    NodeOutput,
)
from app.modules.nodes.descriptors import (
    DisplayOptions,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class WaitNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.wait",
        version=1,
        name="Wait",
        group="flow",
        category="Core",
        description="Pause the execution for a fixed time, or until resumed externally.",
        icon="clock",
        color="cat-flow",
        aliases=["delay", "pause", "sleep", "approval"],
        subtitle="={{ $parameter.mode }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=False,
        properties=[
            NodeProperty(
                name="mode",
                display_name="Mode",
                type="options",
                default="duration",
                options=[
                    PropertyOption(label="For a duration", value="duration"),
                    PropertyOption(
                        label="Until resumed (webhook/approval)", value="webhook"
                    ),
                ],
            ),
            NodeProperty(
                name="durationSeconds",
                display_name="Duration (seconds)",
                type="number",
                default=60,
                display_options=DisplayOptions(show={"mode": ["duration"]}),
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        mode = params.get("mode", "duration")
        resume_token = secrets.token_urlsafe(32)
        if mode == "duration":
            seconds = float(params.get("durationSeconds", 60) or 0)
            raise ExecutionSuspended(
                resume_token=resume_token,
                resume_after=datetime.now(UTC) + timedelta(seconds=seconds),
            )
        raise ExecutionSuspended(resume_token=resume_token, resume_after=None)
