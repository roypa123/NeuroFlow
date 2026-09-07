"""Project business rules. Framework-agnostic -- see
docs/08-backend-architecture.md #8.1.

Access control for a project is "any member of its organization can read;
`owner`/`admin`/`member` can write, `viewer` cannot" -- a plain role
comparison rather than a new `Permission` enum member, since nothing else
needs one yet. The role comparison itself is an authorization *decision*,
so it stays in the controller (see app/core/permissions.py's docstring on
`require()`); this service only ever answers "what is this user's role
here", never "is that enough".
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.permissions import Role
from app.modules.audit.service import AuditService
from app.modules.organizations.service import OrganizationService
from app.modules.projects.exceptions import (
    CannotDeletePersonalProjectError,
    ProjectNotFoundError,
)
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        organizations: OrganizationService,
        audit: AuditService,
    ) -> None:
        self._projects = projects
        self._organizations = organizations
        self._audit = audit

    async def get_role_for_organization(
        self, *, organization_id: UUID, user_id: UUID
    ) -> Role:
        return await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=user_id
        )

    async def get(self, *, project_id: UUID, user_id: UUID) -> tuple[Project, Role]:
        project = await self._projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        role = await self.get_role_for_organization(
            organization_id=project.organization_id, user_id=user_id
        )
        return project, role

    async def list_for_organization(
        self, *, organization_id: UUID, user_id: UUID
    ) -> tuple[list[Project], Role]:
        role = await self.get_role_for_organization(
            organization_id=organization_id, user_id=user_id
        )
        projects = await self._projects.list_by_organization(organization_id)
        return projects, role

    async def create(
        self, *, organization_id: UUID, name: str, actor_id: UUID
    ) -> Project:
        project = await self._projects.create(
            organization_id=organization_id, name=name
        )
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="project.created",
            resource_type="project",
            resource_id=project.id,
            changes={"name": {"from": None, "to": name}},
        )
        return project

    async def update(self, *, project: Project, name: str, actor_id: UUID) -> Project:
        old_name = project.name
        await self._projects.update_name(project, name=name)
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="project.updated",
            resource_type="project",
            resource_id=project.id,
            changes={"name": {"from": old_name, "to": name}},
        )
        return project

    async def delete(self, *, project: Project, actor_id: UUID) -> None:
        if project.is_personal:
            raise CannotDeletePersonalProjectError(
                "The organization's Personal project cannot be deleted"
            )
        await self._projects.soft_delete(project, at=datetime.now(UTC))
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="project.deleted",
            resource_type="project",
            resource_id=project.id,
        )
