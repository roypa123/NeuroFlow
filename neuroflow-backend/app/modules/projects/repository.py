"""SQL access for projects. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, organization_id: UUID, name: str) -> Project:
        project = Project(organization_id=organization_id, name=name)
        self._session.add(project)
        await self._session.flush()
        return project
