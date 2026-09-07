"""Workflow business rules. Framework-agnostic -- raises AppError
subclasses, never HTTPException. See docs/08-backend-architecture.md #8.1.

Access is resolved via `ProjectService.get`, the same project->org->role
chokepoint `projects` already uses: a workflow in a project the caller
isn't a member of 404s (via the project lookup failing), never 403s -- see
docs/17-testing-strategy.md #17.4.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.pagination import Cursor, build_keyset_page, clamp_limit
from app.core.permissions import Role
from app.modules.audit.service import AuditService
from app.modules.nodes.exceptions import NodeTypeNotFoundError
from app.modules.nodes.service import NodeTypeService
from app.modules.projects.models import Project
from app.modules.projects.service import ProjectService
from app.modules.workflows.exceptions import (
    WorkflowNotFoundError,
    WorkflowValidationError,
    WorkflowVersionConflictError,
    WorkflowVersionNotFoundError,
)
from app.modules.workflows.models import Workflow, WorkflowVersion
from app.modules.workflows.repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)
from app.modules.workflows.schemas import WorkflowGraph, WorkflowSettings


def _compute_checksum(graph: dict[str, Any]) -> str:
    canonical = json.dumps(graph, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class WorkflowService:
    def __init__(
        self,
        workflows: WorkflowRepository,
        versions: WorkflowVersionRepository,
        projects: ProjectService,
        node_types: NodeTypeService,
        audit: AuditService,
    ) -> None:
        self._workflows = workflows
        self._versions = versions
        self._projects = projects
        self._node_types = node_types
        self._audit = audit

    async def _get_project_and_role(
        self, *, project_id: UUID, user_id: UUID
    ) -> tuple[Project, Role]:
        return await self._projects.get(project_id=project_id, user_id=user_id)

    async def get_role_for_project(
        self, *, project_id: UUID, user_id: UUID
    ) -> Role:
        _project, role = await self._get_project_and_role(
            project_id=project_id, user_id=user_id
        )
        return role

    async def get(
        self, *, workflow_id: UUID, user_id: UUID
    ) -> tuple[Workflow, Project, Role]:
        workflow = await self._workflows.get_by_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError("Workflow not found")
        project, role = await self._get_project_and_role(
            project_id=workflow.project_id, user_id=user_id
        )
        return workflow, project, role

    async def get_active_version(self, workflow: Workflow) -> WorkflowVersion:
        version: WorkflowVersion | None = None
        if workflow.active_version_id is not None:
            version = await self._versions.get_by_id(workflow.active_version_id)
        if version is None:
            version = await self._versions.get_latest(workflow.id)
        if version is None:
            raise WorkflowNotFoundError("Workflow has no versions")
        return version

    async def list_for_project(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        search: str | None,
        is_active: bool | None,
        limit: int | None,
        cursor_token: str | None,
    ) -> tuple[list[Workflow], dict[UUID, int], str | None, bool]:
        await self._get_project_and_role(project_id=project_id, user_id=user_id)
        page_limit = clamp_limit(limit)
        cursor = Cursor.decode(cursor_token) if cursor_token else None
        rows = await self._workflows.list_by_project(
            project_id,
            search=search,
            is_active=is_active,
            limit=page_limit,
            cursor=(cursor.created_at, cursor.id) if cursor else None,
        )
        page_rows, next_cursor, has_more = build_keyset_page(rows, limit=page_limit)
        version_numbers = await self._versions.get_latest_version_numbers(
            [w.id for w in page_rows]
        )
        return page_rows, version_numbers, next_cursor, has_more

    async def create(
        self, *, project_id: UUID, name: str, description: str | None, actor_id: UUID
    ) -> tuple[Workflow, WorkflowVersion]:
        project, _role = await self._get_project_and_role(
            project_id=project_id, user_id=actor_id
        )
        settings = WorkflowSettings().model_dump(mode="json")
        workflow = await self._workflows.create(
            project_id=project_id,
            name=name,
            description=description,
            created_by=actor_id,
            settings=settings,
        )
        graph = WorkflowGraph().model_dump(mode="json")
        version = await self._versions.create(
            workflow_id=workflow.id,
            version=1,
            graph=graph,
            checksum=_compute_checksum(graph),
            note=None,
            created_by=actor_id,
        )
        await self._workflows.set_active_version(workflow, version.id)
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="workflow.created",
            resource_type="workflow",
            resource_id=workflow.id,
            changes={"name": {"from": None, "to": name}},
        )
        return workflow, version

    def _collect_graph_errors(self, graph: WorkflowGraph) -> list[str]:
        errors: list[str] = []
        ids = [node.id for node in graph.nodes]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate node ids in graph")
        id_set = set(ids)
        for node in graph.nodes:
            try:
                self._node_types.get(node.type)
            except NodeTypeNotFoundError:
                errors.append(f"Unknown node type: {node.type}")
        for edge in graph.edges:
            if edge.source not in id_set or edge.target not in id_set:
                errors.append(f"Edge {edge.id} references an unknown node")
        return errors

    def validate(self, graph: WorkflowGraph) -> list[str]:
        return self._collect_graph_errors(graph)

    def _validate_graph(self, graph: WorkflowGraph) -> None:
        errors = self._collect_graph_errors(graph)
        if errors:
            raise WorkflowValidationError(errors[0], details={"errors": errors})

    async def update(
        self,
        *,
        workflow: Workflow,
        organization_id: UUID,
        actor_id: UUID,
        name: str | None = None,
        description: str | None = None,
        settings: WorkflowSettings | None = None,
        graph: WorkflowGraph | None = None,
        base_version_id: UUID | None = None,
        note: str | None = None,
    ) -> tuple[Workflow, WorkflowVersion]:
        changes: dict[str, Any] = {}
        if name is not None and name != workflow.name:
            changes["name"] = {"from": workflow.name, "to": name}
        settings_dict = (
            settings.model_dump(mode="json") if settings is not None else None
        )
        await self._workflows.update(
            workflow, name=name, description=description, settings=settings_dict
        )

        latest = await self._versions.get_latest(workflow.id)
        version = latest
        if graph is not None:
            if latest is not None and (
                base_version_id is None or base_version_id != latest.id
            ):
                raise WorkflowVersionConflictError(
                    "This workflow was modified by someone else.",
                    details={
                        "expectedVersionId": str(base_version_id)
                        if base_version_id
                        else None,
                        "actualVersionId": str(latest.id),
                    },
                )
            self._validate_graph(graph)
            graph_dict = graph.model_dump(mode="json")
            checksum = _compute_checksum(graph_dict)
            if latest is None or latest.checksum != checksum:
                next_number = (latest.version + 1) if latest else 1
                version = await self._versions.create(
                    workflow_id=workflow.id,
                    version=next_number,
                    graph=graph_dict,
                    checksum=checksum,
                    note=note,
                    created_by=actor_id,
                )
                await self._workflows.set_active_version(workflow, version.id)
                changes["graph"] = {"version": next_number}

        if version is None:
            raise WorkflowNotFoundError("Workflow has no versions")
        if changes:
            await self._audit.record(
                organization_id=organization_id,
                actor_id=actor_id,
                action="workflow.updated",
                resource_type="workflow",
                resource_id=workflow.id,
                changes=changes,
            )
        return workflow, version

    async def activate(
        self, *, workflow: Workflow, organization_id: UUID, actor_id: UUID
    ) -> Workflow:
        latest = await self._versions.get_latest(workflow.id)
        graph = (
            WorkflowGraph.model_validate(latest.graph) if latest else WorkflowGraph()
        )
        trigger_count = 0
        for node in graph.nodes:
            try:
                descriptor = self._node_types.get(node.type)
            except NodeTypeNotFoundError:
                continue
            if descriptor.group == "trigger":
                trigger_count += 1
        if trigger_count != 1:
            raise WorkflowValidationError(
                "A workflow must have exactly one trigger node to activate"
            )
        # Real trigger registration (webhooks/schedules) is Phase 5 -- see
        # this phase's plan. Activation here only flips the flag once the
        # graph is structurally activatable.
        await self._workflows.set_active(workflow, is_active=True)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="workflow.activated",
            resource_type="workflow",
            resource_id=workflow.id,
        )
        return workflow

    async def deactivate(
        self, *, workflow: Workflow, organization_id: UUID, actor_id: UUID
    ) -> Workflow:
        await self._workflows.set_active(workflow, is_active=False)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="workflow.deactivated",
            resource_type="workflow",
            resource_id=workflow.id,
        )
        return workflow

    async def duplicate(
        self,
        *,
        workflow: Workflow,
        organization_id: UUID,
        actor_id: UUID,
        name: str | None = None,
    ) -> tuple[Workflow, WorkflowVersion]:
        latest = await self._versions.get_latest(workflow.id)
        graph_dict = latest.graph if latest else WorkflowGraph().model_dump(mode="json")
        new_name = name or f"{workflow.name} (copy)"
        new_workflow = await self._workflows.create(
            project_id=workflow.project_id,
            name=new_name,
            description=workflow.description,
            created_by=actor_id,
            settings=workflow.settings,
        )
        checksum = _compute_checksum(graph_dict)
        version = await self._versions.create(
            workflow_id=new_workflow.id,
            version=1,
            graph=graph_dict,
            checksum=checksum,
            note=f"Duplicated from {workflow.id}",
            created_by=actor_id,
        )
        await self._workflows.set_active_version(new_workflow, version.id)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="workflow.duplicated",
            resource_type="workflow",
            resource_id=new_workflow.id,
            changes={"sourceWorkflowId": str(workflow.id)},
        )
        return new_workflow, version

    async def export_graph(self, *, workflow: Workflow) -> WorkflowGraph:
        version = await self.get_active_version(workflow)
        return WorkflowGraph.model_validate(version.graph)

    async def import_(
        self,
        *,
        project_id: UUID,
        actor_id: UUID,
        name: str,
        description: str | None,
        settings: WorkflowSettings,
        graph: WorkflowGraph,
    ) -> tuple[Workflow, WorkflowVersion]:
        project, _role = await self._get_project_and_role(
            project_id=project_id, user_id=actor_id
        )
        self._validate_graph(graph)
        workflow = await self._workflows.create(
            project_id=project_id,
            name=name,
            description=description,
            created_by=actor_id,
            settings=settings.model_dump(mode="json"),
        )
        graph_dict = graph.model_dump(mode="json")
        version = await self._versions.create(
            workflow_id=workflow.id,
            version=1,
            graph=graph_dict,
            checksum=_compute_checksum(graph_dict),
            note="Imported",
            created_by=actor_id,
        )
        await self._workflows.set_active_version(workflow, version.id)
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="workflow.imported",
            resource_type="workflow",
            resource_id=workflow.id,
        )
        return workflow, version

    async def list_versions(self, *, workflow_id: UUID) -> list[WorkflowVersion]:
        return await self._versions.list_for_workflow(workflow_id)

    async def get_version(
        self, *, workflow_id: UUID, version_number: int
    ) -> WorkflowVersion:
        version = await self._versions.get_by_number(workflow_id, version_number)
        if version is None:
            raise WorkflowVersionNotFoundError("Version not found")
        return version

    async def restore_version(
        self,
        *,
        workflow: Workflow,
        organization_id: UUID,
        actor_id: UUID,
        version_id: UUID,
    ) -> tuple[Workflow, WorkflowVersion]:
        target = await self._versions.get_by_id(version_id)
        if target is None or target.workflow_id != workflow.id:
            raise WorkflowVersionNotFoundError("Version not found")
        latest = await self._versions.get_latest(workflow.id)
        version = latest
        if latest is None or latest.checksum != target.checksum:
            next_number = (latest.version + 1) if latest else 1
            version = await self._versions.create(
                workflow_id=workflow.id,
                version=next_number,
                graph=target.graph,
                checksum=target.checksum,
                note=f"Restored from v{target.version}",
                created_by=actor_id,
            )
            await self._workflows.set_active_version(workflow, version.id)
        if version is None:
            raise WorkflowNotFoundError("Workflow has no versions")
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="workflow.version_restored",
            resource_type="workflow",
            resource_id=workflow.id,
            changes={"restoredFromVersion": target.version},
        )
        return workflow, version

    async def delete(
        self, *, workflow: Workflow, organization_id: UUID, actor_id: UUID
    ) -> None:
        await self._workflows.soft_delete(workflow, at=datetime.now(UTC))
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="workflow.deleted",
            resource_type="workflow",
            resource_id=workflow.id,
        )
