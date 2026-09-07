"""Project orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.exceptions import PermissionError as AppPermissionError
from app.core.permissions import Role
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.projects.service import ProjectService


def _require_write_role(role: Role) -> None:
    if role == Role.VIEWER:
        raise AppPermissionError("Viewers cannot modify projects")


def _to_read(project: Project) -> ProjectRead:
    return ProjectRead.model_validate(project)


class ProjectController:
    def __init__(self, service: ProjectService) -> None:
        self._service = service

    async def list_for_organization(
        self, ctx: RequestContext, organization_id: UUID
    ) -> list[ProjectRead]:
        projects, _role = await self._service.list_for_organization(
            organization_id=organization_id, user_id=ctx.user_id
        )
        return [_to_read(project) for project in projects]

    async def create(self, ctx: RequestContext, payload: ProjectCreate) -> ProjectRead:
        role = await self._service.get_role_for_organization(
            organization_id=payload.organization_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        project = await self._service.create(
            organization_id=payload.organization_id,
            name=payload.name,
            actor_id=ctx.user_id,
        )
        return _to_read(project)

    async def get(self, ctx: RequestContext, project_id: UUID) -> ProjectRead:
        project, _role = await self._service.get(
            project_id=project_id, user_id=ctx.user_id
        )
        return _to_read(project)

    async def update(
        self, ctx: RequestContext, project_id: UUID, payload: ProjectUpdate
    ) -> ProjectRead:
        project, role = await self._service.get(
            project_id=project_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        project = await self._service.update(
            project=project, name=payload.name, actor_id=ctx.user_id
        )
        return _to_read(project)

    async def delete(self, ctx: RequestContext, project_id: UUID) -> None:
        project, role = await self._service.get(
            project_id=project_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        await self._service.delete(project=project, actor_id=ctx.user_id)
