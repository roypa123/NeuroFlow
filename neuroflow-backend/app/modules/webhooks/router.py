"""Webhook display routes: declarations only. See docs/11-api-design.md
#11.12. The inbound ingress endpoints (`/webhook/{path}`,
`/webhook-test/{path}`) live in `ingress_router.py`, mounted outside
`/api/v1` in `app.main` -- these two are the authenticated, `/api/v1`-side
"what URL do I paste into Stripe" endpoints the editor calls.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import RequestContextDep
from app.modules.webhooks.dependencies import WebhookControllerDep
from app.modules.webhooks.schemas import TestWebhookRequest, WebhookRegistrationRead

router = APIRouter(tags=["webhooks"])


@router.get(
    "/workflows/{workflow_id}/webhooks", response_model=list[WebhookRegistrationRead]
)
async def list_workflow_webhooks(
    workflow_id: UUID, ctx: RequestContextDep, controller: WebhookControllerDep
) -> list[WebhookRegistrationRead]:
    return await controller.list_for_workflow(ctx, workflow_id)


@router.post(
    "/workflows/{workflow_id}/webhooks/test-listen",
    response_model=WebhookRegistrationRead,
)
async def listen_for_test_webhook(
    workflow_id: UUID,
    payload: TestWebhookRequest,
    ctx: RequestContextDep,
    controller: WebhookControllerDep,
) -> WebhookRegistrationRead:
    return await controller.listen_for_test(ctx, workflow_id, payload)
