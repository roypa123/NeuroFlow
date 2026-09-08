"""Webhook ingress logic: match a path/method to a registration, verify
its auth, create the execution, and honor the response mode. Called by
`ingress_router.py`, mounted outside `/api/v1` -- see docs/09-domain-
modules.md #9.11 and docs/11-api-design.md #11.12.

`response_node` is explicitly deferred (needs a Phase-6 "Respond to
Webhook" node) -- see this phase's plan Scope decisions. `immediate` and
`last_node` are implemented.

Execution creation goes straight through `ExecutionRepository`, not
`ExecutionService.create_and_enqueue`: there is no authenticated actor on
an inbound third-party request, so the workflow is resolved the same
actor-free way `app.nodes.execute_workflow` resolves a sub-workflow.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.core.database import session_scope
from app.core.queue import get_arq_pool
from app.core.redis import get_redis
from app.modules.executions.repository import ExecutionRepository
from app.modules.executions.waiting import (
    load_last_output_items,
    subscribe,
    wait_for_finish,
)
from app.modules.webhooks.repository import WebhookRepository
from app.modules.webhooks.service import WebhookService, verify_signature
from app.modules.workflows.repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)

LAST_NODE_TIMEOUT_SECONDS = 30.0


async def handle_webhook_request(
    request: Request, path: str, *, is_test: bool
) -> Response:
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    async with session_scope() as session:
        webhooks = WebhookService(WebhookRepository(session))
        registration = await webhooks.find_active(
            path=path, method=request.method, is_test=is_test
        )
        if registration is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)

        if not verify_signature(registration.auth, raw_body=raw_body, headers=headers):
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)

        body_json: Any
        try:
            body_json = json.loads(raw_body) if raw_body else {}
        except ValueError:
            body_json = {"raw": raw_body.decode(errors="replace")}

        trigger_data = {
            "body": body_json,
            "headers": headers,
            "query": dict(request.query_params),
            "method": request.method,
        }

        workflow_repo = WorkflowRepository(session)
        version_repo = WorkflowVersionRepository(session)
        workflow = await workflow_repo.get_by_id(registration.workflow_id)
        if workflow is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        version = None
        if workflow.active_version_id is not None:
            version = await version_repo.get_by_id(workflow.active_version_id)
        if version is None:
            version = await version_repo.get_latest(workflow.id)
        if version is None:
            return Response(status_code=status.HTTP_404_NOT_FOUND)

        execution_repo = ExecutionRepository(session)
        execution = await execution_repo.create(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            project_id=workflow.project_id,
            mode="webhook",
            trigger_data=trigger_data,
            created_by=None,
            created_at=datetime.now(UTC),
        )
        execution_id = execution.id
        response_mode = registration.response_mode

    pubsub = None
    if response_mode == "last_node":
        # Subscribe *before* enqueueing so the worker cannot publish
        # execution.finished into a channel nothing is listening to yet.
        pubsub = await subscribe(get_redis(), execution_id)

    pool = await get_arq_pool()
    await pool.enqueue_job("run_execution", execution_id)

    if pubsub is None:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"executionId": str(execution_id)},
        )

    result_status = await wait_for_finish(
        pubsub, timeout_seconds=LAST_NODE_TIMEOUT_SECONDS
    )
    items = (
        await load_last_output_items(execution_id) if result_status == "success" else []
    )
    body = (
        items[0].json_
        if items
        else {"executionId": str(execution_id), "status": result_status}
    )
    return JSONResponse(content=body)
