"""Execute Workflow -- calls another workflow as a sub-workflow, optionally
waiting for it to finish. Runs inside the worker, so it talks to the
executions/workflows repositories and the arq queue directly rather than
through `ExecutionService`'s actor-authorization wrapper: the parent
execution is already authorized and running, and there is no interactive
actor at this point to check a role against -- only the worker. See
docs/13-node-catalog-and-sdk.md #13.5 ("Execute Sub-workflow") and this
phase's plan finding #7.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.database import session_scope
from app.core.queue import get_arq_pool
from app.core.redis import get_redis
from app.modules.executions.repository import ExecutionRepository
from app.modules.executions.waiting import (
    load_last_output_items,
    subscribe,
    wait_for_finish,
)
from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)
from app.modules.workflows.repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)

_MAX_WAIT_SECONDS = 600.0


class ExecuteWorkflowNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.executeWorkflow",
        version=1,
        name="Execute Workflow",
        group="flow",
        category="Core",
        description="Runs another workflow as a sub-workflow.",
        icon="git-branch",
        color="cat-flow",
        aliases=["subworkflow", "call"],
        subtitle="={{ $parameter.workflowId }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=False,
        properties=[
            NodeProperty(
                name="workflowId",
                display_name="Workflow",
                type="string",
                required=True,
                description="The id of the workflow to run.",
            ),
            NodeProperty(
                name="waitForCompletion",
                display_name="Wait For Completion",
                type="boolean",
                default=True,
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        workflow_id = UUID(params["workflowId"])
        wait = bool(params.get("waitForCompletion", True))
        parent_execution_id = UUID(ctx.execution.id) if ctx.execution else None

        async with session_scope() as session:
            workflow_repo = WorkflowRepository(session)
            version_repo = WorkflowVersionRepository(session)
            execution_repo = ExecutionRepository(session)

            workflow = await workflow_repo.get_by_id(workflow_id)
            if workflow is None:
                raise ValueError(f"Sub-workflow not found: {workflow_id}")
            version = None
            if workflow.active_version_id is not None:
                version = await version_repo.get_by_id(workflow.active_version_id)
            if version is None:
                version = await version_repo.get_latest(workflow.id)
            if version is None:
                raise ValueError(f"Sub-workflow has no versions: {workflow_id}")

            child = await execution_repo.create(
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                project_id=workflow.project_id,
                mode="sub",
                trigger_data={"items": [item.json_ for item in ctx.input_items]},
                created_by=None,
                created_at=datetime.now(UTC),
            )
            child.parent_execution_id = parent_execution_id
            await session.flush()
            child_id = child.id

        pubsub = None
        if wait:
            pubsub = await subscribe(get_redis(), child_id)

        pool = await get_arq_pool()
        await pool.enqueue_job("run_execution", child_id)

        if pubsub is None:
            return {"main": [[Item(json={"executionId": str(child_id)})]]}

        status = await wait_for_finish(pubsub, timeout_seconds=_MAX_WAIT_SECONDS)
        output_items = (
            await load_last_output_items(child_id) if status == "success" else []
        )
        if not output_items:
            output_items = [Item(json={"executionId": str(child_id), "status": status})]
        return {"main": [output_items]}
