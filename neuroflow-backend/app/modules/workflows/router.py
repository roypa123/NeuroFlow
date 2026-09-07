"""Workflow routes: declarations only. Endpoint set mirrors
docs/11-api-design.md #11.7 (execute/pinned-data deferred to Phase 4
alongside real execution -- see this phase's plan)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import RequestContextDep
from app.core.pagination import KeysetPage
from app.modules.workflows.dependencies import WorkflowControllerDep
from app.modules.workflows.schemas import (
    WorkflowCreate,
    WorkflowDuplicateRequest,
    WorkflowExport,
    WorkflowImportRequest,
    WorkflowRead,
    WorkflowSummary,
    WorkflowUpdate,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowVersionDetail,
    WorkflowVersionRead,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

ProjectIdQuery = Annotated[UUID, Query(alias="projectId")]


@router.get("", response_model=KeysetPage[WorkflowSummary])
async def list_workflows(
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
    project_id: ProjectIdQuery,
    search: str | None = None,
    is_active: Annotated[bool | None, Query(alias="isActive")] = None,
    limit: int | None = None,
    cursor: str | None = None,
) -> KeysetPage[WorkflowSummary]:
    return await controller.list_for_project(
        ctx, project_id, search=search, is_active=is_active, limit=limit, cursor=cursor
    )


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> WorkflowRead:
    return await controller.create(ctx, payload)


@router.post(
    "/import", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED
)
async def import_workflow(
    payload: WorkflowImportRequest,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowRead:
    return await controller.import_workflow(ctx, payload)


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> WorkflowRead:
    return await controller.get(ctx, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowRead:
    return await controller.update(ctx, workflow_id, payload)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> None:
    await controller.delete(ctx, workflow_id)


@router.post("/{workflow_id}/activate", response_model=WorkflowRead)
async def activate_workflow(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> WorkflowRead:
    return await controller.activate(ctx, workflow_id)


@router.post("/{workflow_id}/deactivate", response_model=WorkflowRead)
async def deactivate_workflow(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> WorkflowRead:
    return await controller.deactivate(ctx, workflow_id)


@router.post(
    "/{workflow_id}/duplicate",
    response_model=WorkflowRead,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_workflow(
    workflow_id: UUID,
    payload: WorkflowDuplicateRequest,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowRead:
    return await controller.duplicate(ctx, workflow_id, payload)


@router.get("/{workflow_id}/export", response_model=WorkflowExport)
async def export_workflow(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> WorkflowExport:
    return await controller.export(ctx, workflow_id)


@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResponse)
async def validate_workflow(
    workflow_id: UUID,
    payload: WorkflowValidateRequest,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowValidateResponse:
    return await controller.validate(ctx, workflow_id, payload)


@router.get("/{workflow_id}/versions", response_model=list[WorkflowVersionRead])
async def list_workflow_versions(
    workflow_id: UUID, ctx: RequestContextDep, controller: WorkflowControllerDep
) -> list[WorkflowVersionRead]:
    return await controller.list_versions(ctx, workflow_id)


@router.get(
    "/{workflow_id}/versions/{version_number}", response_model=WorkflowVersionDetail
)
async def get_workflow_version(
    workflow_id: UUID,
    version_number: int,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowVersionDetail:
    return await controller.get_version(ctx, workflow_id, version_number)


@router.post(
    "/{workflow_id}/versions/{version_id}/restore", response_model=WorkflowRead
)
async def restore_workflow_version(
    workflow_id: UUID,
    version_id: UUID,
    ctx: RequestContextDep,
    controller: WorkflowControllerDep,
) -> WorkflowRead:
    return await controller.restore_version(ctx, workflow_id, version_id)
