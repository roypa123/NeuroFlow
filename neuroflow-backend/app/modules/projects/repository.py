"""SQL access for projects. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, organization_id: UUID, name: str, is_personal: bool = False
    ) -> Project:
        project = Project(
            organization_id=organization_id, name=name, is_personal=is_personal
        )
        self._session.add(project)
        await self._session.flush()
        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id, Project.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> list[Project]:
        stmt = (
            select(Project)
            .where(
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_name(self, project: Project, *, name: str) -> None:
        project.name = name

    async def soft_delete(self, project: Project, *, at: datetime) -> None:
        project.deleted_at = at
