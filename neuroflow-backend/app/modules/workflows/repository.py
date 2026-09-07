"""SQL access for workflows and their versions. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workflows.models import Workflow, WorkflowVersion


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        name: str,
        description: str | None,
        created_by: UUID,
        settings: dict[str, Any],
    ) -> Workflow:
        workflow = Workflow(
            project_id=project_id,
            name=name,
            description=description,
            created_by=created_by,
            settings=settings,
        )
        self._session.add(workflow)
        await self._session.flush()
        return workflow

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        stmt = select(Workflow).where(
            Workflow.id == workflow_id, Workflow.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        search: str | None,
        is_active: bool | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[Workflow]:
        stmt = select(Workflow).where(
            Workflow.project_id == project_id, Workflow.deleted_at.is_(None)
        )
        if search:
            stmt = stmt.where(Workflow.name.ilike(f"%{search}%"))
        if is_active is not None:
            stmt = stmt.where(Workflow.is_active == is_active)
        if cursor is not None:
            stmt = stmt.where(
                tuple_(Workflow.created_at, Workflow.id) < tuple_(*cursor)
            )
        stmt = stmt.order_by(Workflow.created_at.desc(), Workflow.id.desc()).limit(
            limit + 1
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        workflow: Workflow,
        *,
        name: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        if name is not None:
            workflow.name = name
        if description is not None:
            workflow.description = description
        if settings is not None:
            workflow.settings = settings

    async def set_active_version(
        self, workflow: Workflow, version_id: UUID | None
    ) -> None:
        workflow.active_version_id = version_id

    async def set_active(self, workflow: Workflow, *, is_active: bool) -> None:
        workflow.is_active = is_active

    async def soft_delete(self, workflow: Workflow, *, at: datetime) -> None:
        workflow.deleted_at = at


class WorkflowVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workflow_id: UUID,
        version: int,
        graph: dict[str, Any],
        checksum: str,
        note: str | None,
        created_by: UUID,
        pinned_data: dict[str, Any] | None = None,
    ) -> WorkflowVersion:
        row = WorkflowVersion(
            workflow_id=workflow_id,
            version=version,
            graph=graph,
            checksum=checksum,
            note=note,
            created_by=created_by,
            pinned_data=pinned_data,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_latest(self, workflow_id: UUID) -> WorkflowVersion | None:
        stmt = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, version_id: UUID) -> WorkflowVersion | None:
        stmt = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(
        self, workflow_id: UUID, version: int
    ) -> WorkflowVersion | None:
        stmt = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workflow(self, workflow_id: UUID) -> list[WorkflowVersion]:
        stmt = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.version.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def next_version_number(self, workflow_id: UUID) -> int:
        stmt = select(func.max(WorkflowVersion.version)).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        result = await self._session.execute(stmt)
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def get_latest_version_numbers(
        self, workflow_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Batched, so listing N workflows costs one query, not N -- see
        docs/03-system-architecture.md #3.8's "no unbounded list endpoint
        does an unbounded number of queries" spirit."""
        if not workflow_ids:
            return {}
        stmt = (
            select(WorkflowVersion.workflow_id, func.max(WorkflowVersion.version))
            .where(WorkflowVersion.workflow_id.in_(workflow_ids))
            .group_by(WorkflowVersion.workflow_id)
        )
        result = await self._session.execute(stmt)
        return dict(result.all())
