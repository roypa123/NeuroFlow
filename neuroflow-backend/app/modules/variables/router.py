"""Variable routes: declarations only. See docs/11-api-design.md #11.12."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import RequestContextDep
from app.modules.variables.dependencies import VariableControllerDep
from app.modules.variables.schemas import VariableCreate, VariableRead, VariableUpdate

router = APIRouter(prefix="/variables", tags=["variables"])

OrganizationIdQuery = Annotated[UUID, Query(alias="organizationId")]
ProjectIdQuery = Annotated[UUID | None, Query(alias="projectId")]


@router.get("", response_model=list[VariableRead])
async def list_variables(
    ctx: RequestContextDep,
    controller: VariableControllerDep,
    organization_id: OrganizationIdQuery,
    project_id: ProjectIdQuery = None,
) -> list[VariableRead]:
    return await controller.list_for_org(ctx, organization_id, project_id=project_id)


@router.post("", response_model=VariableRead, status_code=status.HTTP_201_CREATED)
async def create_variable(
    payload: VariableCreate,
    ctx: RequestContextDep,
    controller: VariableControllerDep,
    organization_id: OrganizationIdQuery,
) -> VariableRead:
    return await controller.create(ctx, organization_id, payload)


@router.patch("/{variable_id}", response_model=VariableRead)
async def update_variable(
    variable_id: UUID,
    payload: VariableUpdate,
    ctx: RequestContextDep,
    controller: VariableControllerDep,
) -> VariableRead:
    return await controller.update(ctx, variable_id, payload)


@router.delete("/{variable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variable(
    variable_id: UUID, ctx: RequestContextDep, controller: VariableControllerDep
) -> None:
    await controller.delete(ctx, variable_id)
