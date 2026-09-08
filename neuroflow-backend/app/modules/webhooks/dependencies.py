"""DI wiring for the webhooks module. See docs/08-backend-architecture.md
#8.4."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.webhooks.controller import WebhookController
from app.modules.webhooks.repository import WebhookRepository
from app.modules.webhooks.service import WebhookService
from app.modules.workflows.dependencies import WorkflowServiceDep


def get_webhook_service(session: SessionDep) -> WebhookService:
    return WebhookService(WebhookRepository(session))


WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]


def get_webhook_controller(
    service: WebhookServiceDep, workflows: WorkflowServiceDep
) -> WebhookController:
    return WebhookController(service, workflows)


WebhookControllerDep = Annotated[WebhookController, Depends(get_webhook_controller)]
