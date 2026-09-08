"""Webhook orchestration for the `/workflows/{id}/webhooks` read/test
endpoints -- registration itself happens inside `WorkflowService.activate`,
not here. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.permissions import Permission, require
from app.modules.webhooks.exceptions import WebhookNotFoundError
from app.modules.webhooks.models import WebhookRegistration
from app.modules.webhooks.schemas import TestWebhookRequest, WebhookRegistrationRead
from app.modules.webhooks.service import WebhookService, auth_spec_from_node_params
from app.modules.workflows.schemas import WorkflowGraph
from app.modules.workflows.service import WorkflowService


class WebhookController:
    def __init__(self, webhooks: WebhookService, workflows: WorkflowService) -> None:
        self._webhooks = webhooks
        self._workflows = workflows

    async def list_for_workflow(
        self, ctx: RequestContext, workflow_id: UUID
    ) -> list[WebhookRegistrationRead]:
        _workflow, _project, role = await self._workflows.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        rows = await self._webhooks.list_for_workflow(workflow_id)
        return [self._to_read(row) for row in rows]

    async def listen_for_test(
        self, ctx: RequestContext, workflow_id: UUID, payload: TestWebhookRequest
    ) -> WebhookRegistrationRead:
        workflow, _project, role = await self._workflows.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        version = await self._workflows.get_active_version(workflow)
        graph = WorkflowGraph.model_validate(version.graph)
        node = next((n for n in graph.nodes if n.id == payload.node_id), None)
        if node is None:
            raise WebhookNotFoundError("Webhook trigger node not found in the graph")
        row = await self._webhooks.register_test(
            workflow_id=workflow.id,
            node_id=node.id,
            path=node.parameters.get("path") or str(node.id),
            method=node.parameters.get("method", "POST"),
            auth=auth_spec_from_node_params(node.parameters),
            response_mode=node.parameters.get("responseMode", "immediate"),
        )
        return self._to_read(row)

    def _to_read(self, row: WebhookRegistration) -> WebhookRegistrationRead:
        return WebhookRegistrationRead(
            id=row.id,
            node_id=row.node_id,
            path=row.path,
            method=row.method,
            is_test=row.is_test,
            response_mode=row.response_mode,
            url=self._webhooks.build_url(path=row.path, is_test=row.is_test),
        )
