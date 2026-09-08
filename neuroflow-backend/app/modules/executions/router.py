"""Execution routes: declarations only. Endpoint set mirrors
docs/11-api-design.md #11.8 minus `/resume` (suspension/resume is Phase 5 --
see this phase's plan's Scope decisions)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import RequestContextDep
from app.core.pagination import KeysetPage
from app.modules.executions.dependencies import ExecutionControllerDep
from app.modules.executions.schemas import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    ExecutionRead,
    ExecutionStatsResponse,
    ExecutionSummary,
    NodeDataRead,
    RetryRequest,
)

router = APIRouter(prefix="/executions", tags=["executions"])

ProjectIdQuery = Annotated[UUID, Query(alias="projectId")]


@router.get("", response_model=KeysetPage[ExecutionSummary])
async def list_executions(
    ctx: RequestContextDep,
    controller: ExecutionControllerDep,
    project_id: ProjectIdQuery,
    workflow_id: Annotated[UUID | None, Query(alias="workflowId")] = None,
    status: str | None = None,
    mode: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
) -> KeysetPage[ExecutionSummary]:
    return await controller.list_for_project(
        ctx,
        project_id,
        workflow_id=workflow_id,
        status=status,
        mode=mode,
        limit=limit,
        cursor=cursor,
    )


@router.get("/stats", response_model=ExecutionStatsResponse)
async def execution_stats(
    ctx: RequestContextDep,
    controller: ExecutionControllerDep,
    project_id: ProjectIdQuery,
) -> ExecutionStatsResponse:
    return await controller.stats(ctx, project_id)


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_executions(
    payload: BulkDeleteRequest,
    ctx: RequestContextDep,
    controller: ExecutionControllerDep,
    project_id: ProjectIdQuery,
) -> BulkDeleteResponse:
    return await controller.bulk_delete(ctx, project_id, payload)


@router.get("/{execution_id}", response_model=ExecutionRead)
async def get_execution(
    execution_id: UUID, ctx: RequestContextDep, controller: ExecutionControllerDep
) -> ExecutionRead:
    return await controller.get(ctx, execution_id)


@router.get("/{execution_id}/nodes/{node_id}/data", response_model=NodeDataRead)
async def get_node_data(
    execution_id: UUID,
    node_id: str,
    ctx: RequestContextDep,
    controller: ExecutionControllerDep,
) -> NodeDataRead:
    return await controller.get_node_data(ctx, execution_id, node_id)


@router.post("/{execution_id}/cancel", response_model=ExecutionRead)
async def cancel_execution(
    execution_id: UUID, ctx: RequestContextDep, controller: ExecutionControllerDep
) -> ExecutionRead:
    return await controller.cancel(ctx, execution_id)


@router.post("/{execution_id}/retry", response_model=ExecutionRead)
async def retry_execution(
    execution_id: UUID,
    payload: RetryRequest,
    ctx: RequestContextDep,
    controller: ExecutionControllerDep,
) -> ExecutionRead:
    return await controller.retry(ctx, execution_id, payload)


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: UUID, ctx: RequestContextDep, controller: ExecutionControllerDep
) -> None:
    await controller.delete(ctx, execution_id)


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: UUID, ctx: RequestContextDep, controller: ExecutionControllerDep
) -> StreamingResponse:
    return StreamingResponse(
        controller.stream(ctx, execution_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
