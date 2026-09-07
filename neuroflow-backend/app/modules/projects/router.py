"""Project routes: declarations only -- see docs/08-backend-architecture.md
#8.1. Endpoint set mirrors docs/11-api-design.md #11.6."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import RequestContextDep
from app.modules.projects.dependencies import ProjectControllerDep
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

OrganizationIdQuery = Annotated[UUID, Query(alias="organizationId")]


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    ctx: RequestContextDep,
    controller: ProjectControllerDep,
    organization_id: OrganizationIdQuery,
) -> list[ProjectRead]:
    return await controller.list_for_organization(ctx, organization_id)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, ctx: RequestContextDep, controller: ProjectControllerDep
) -> ProjectRead:
    return await controller.create(ctx, payload)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID, ctx: RequestContextDep, controller: ProjectControllerDep
) -> ProjectRead:
    return await controller.get(ctx, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    ctx: RequestContextDep,
    controller: ProjectControllerDep,
) -> ProjectRead:
    return await controller.update(ctx, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID, ctx: RequestContextDep, controller: ProjectControllerDep
) -> None:
    await controller.delete(ctx, project_id)
