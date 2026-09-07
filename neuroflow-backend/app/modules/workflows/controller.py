"""Workflow orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.pagination import KeysetPage
from app.core.permissions import Permission, require
from app.modules.workflows.models import Workflow, WorkflowVersion
from app.modules.workflows.schemas import (
    WorkflowCreate,
    WorkflowDuplicateRequest,
    WorkflowExport,
    WorkflowImportRequest,
    WorkflowRead,
    WorkflowSettings,
    WorkflowSummary,
    WorkflowUpdate,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowVersionDetail,
    WorkflowVersionRead,
)
from app.modules.workflows.service import WorkflowService


def _to_read(workflow: Workflow, version: WorkflowVersion) -> WorkflowRead:
    return WorkflowRead(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        kind=workflow.kind,
        is_active=workflow.is_active,
        active_version_id=workflow.active_version_id,
        version=version.version,
        settings=WorkflowSettings.model_validate(workflow.settings),
        graph=version.graph,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _to_summary(workflow: Workflow, version_number: int) -> WorkflowSummary:
    return WorkflowSummary(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        kind=workflow.kind,
        is_active=workflow.is_active,
        version=version_number,
        updated_at=workflow.updated_at,
    )


def _to_version_read(version: WorkflowVersion) -> WorkflowVersionRead:
    return WorkflowVersionRead(
        id=version.id,
        version=version.version,
        checksum=version.checksum,
        note=version.note,
        created_by=version.created_by,
        created_at=version.created_at,
    )


def _to_version_detail(version: WorkflowVersion) -> WorkflowVersionDetail:
    return WorkflowVersionDetail(
        id=version.id,
        version=version.version,
        checksum=version.checksum,
        note=version.note,
        created_by=version.created_by,
        created_at=version.created_at,
        graph=version.graph,
    )


class WorkflowController:
    def __init__(self, service: WorkflowService) -> None:
        self._service = service

    async def list_for_project(
        self,
        ctx: RequestContext,
        project_id: UUID,
        *,
        search: str | None,
        is_active: bool | None,
        limit: int | None,
        cursor: str | None,
    ) -> KeysetPage[WorkflowSummary]:
        role = await self._service.get_role_for_project(
            project_id=project_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        (
            rows,
            version_numbers,
            next_cursor,
            has_more,
        ) = await self._service.list_for_project(
            project_id=project_id,
            user_id=ctx.user_id,
            search=search,
            is_active=is_active,
            limit=limit,
            cursor_token=cursor,
        )
        items = [_to_summary(w, version_numbers.get(w.id, 1)) for w in rows]
        return KeysetPage[WorkflowSummary](
            items=items, next_cursor=next_cursor, has_more=has_more
        )

    async def create(
        self, ctx: RequestContext, payload: WorkflowCreate
    ) -> WorkflowRead:
        role = await self._service.get_role_for_project(
            project_id=payload.project_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        workflow, version = await self._service.create(
            project_id=payload.project_id,
            name=payload.name,
            description=payload.description,
            actor_id=ctx.user_id,
        )
        return _to_read(workflow, version)

    async def get(self, ctx: RequestContext, workflow_id: UUID) -> WorkflowRead:
        workflow, _project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        version = await self._service.get_active_version(workflow)
        return _to_read(workflow, version)

    async def update(
        self, ctx: RequestContext, workflow_id: UUID, payload: WorkflowUpdate
    ) -> WorkflowRead:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        workflow, version = await self._service.update(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
            name=payload.name,
            description=payload.description,
            settings=payload.settings,
            graph=payload.graph,
            base_version_id=payload.base_version_id,
            note=payload.note,
        )
        return _to_read(workflow, version)

    async def delete(self, ctx: RequestContext, workflow_id: UUID) -> None:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_DELETE, scopes=ctx.scopes)
        await self._service.delete(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
        )

    async def activate(self, ctx: RequestContext, workflow_id: UUID) -> WorkflowRead:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_ACTIVATE, scopes=ctx.scopes)
        workflow = await self._service.activate(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
        )
        version = await self._service.get_active_version(workflow)
        return _to_read(workflow, version)

    async def deactivate(self, ctx: RequestContext, workflow_id: UUID) -> WorkflowRead:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_ACTIVATE, scopes=ctx.scopes)
        workflow = await self._service.deactivate(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
        )
        version = await self._service.get_active_version(workflow)
        return _to_read(workflow, version)

    async def duplicate(
        self, ctx: RequestContext, workflow_id: UUID, payload: WorkflowDuplicateRequest
    ) -> WorkflowRead:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        new_workflow, version = await self._service.duplicate(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
            name=payload.name,
        )
        return _to_read(new_workflow, version)

    async def export(self, ctx: RequestContext, workflow_id: UUID) -> WorkflowExport:
        workflow, _project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        graph = await self._service.export_graph(workflow=workflow)
        return WorkflowExport(
            name=workflow.name,
            description=workflow.description,
            settings=WorkflowSettings.model_validate(workflow.settings),
            graph=graph,
        )

    async def import_workflow(
        self, ctx: RequestContext, payload: WorkflowImportRequest
    ) -> WorkflowRead:
        role = await self._service.get_role_for_project(
            project_id=payload.project_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        workflow, version = await self._service.import_(
            project_id=payload.project_id,
            actor_id=ctx.user_id,
            name=payload.name,
            description=payload.description,
            settings=payload.settings,
            graph=payload.graph,
        )
        return _to_read(workflow, version)

    async def validate(
        self, ctx: RequestContext, workflow_id: UUID, payload: WorkflowValidateRequest
    ) -> WorkflowValidateResponse:
        _workflow, _project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        errors = self._service.validate(payload.graph)
        return WorkflowValidateResponse(valid=not errors, errors=errors)

    async def list_versions(
        self, ctx: RequestContext, workflow_id: UUID
    ) -> list[WorkflowVersionRead]:
        _workflow, _project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        versions = await self._service.list_versions(workflow_id=workflow_id)
        return [_to_version_read(v) for v in versions]

    async def get_version(
        self, ctx: RequestContext, workflow_id: UUID, version_number: int
    ) -> WorkflowVersionDetail:
        _workflow, _project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        version = await self._service.get_version(
            workflow_id=workflow_id, version_number=version_number
        )
        return _to_version_detail(version)

    async def restore_version(
        self, ctx: RequestContext, workflow_id: UUID, version_id: UUID
    ) -> WorkflowRead:
        workflow, project, role = await self._service.get(
            workflow_id=workflow_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_WRITE, scopes=ctx.scopes)
        workflow, version = await self._service.restore_version(
            workflow=workflow,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
            version_id=version_id,
        )
        return _to_read(workflow, version)
