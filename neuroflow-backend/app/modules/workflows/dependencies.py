"""DI wiring for the workflows module. See docs/08-backend-architecture.md
#8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.nodes.service import NodeTypeService
from app.modules.projects.dependencies import ProjectServiceDep
from app.modules.workflows.controller import WorkflowController
from app.modules.workflows.repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)
from app.modules.workflows.service import WorkflowService


def get_workflow_service(
    session: SessionDep, projects: ProjectServiceDep
) -> WorkflowService:
    # AuditService is built directly here, same reasoning as
    # organizations/projects/dependencies.py: avoids a wiring-layer
    # circular import back into audit/dependencies.py.
    audit = AuditService(AuditRepository(session))
    return WorkflowService(
        workflows=WorkflowRepository(session),
        versions=WorkflowVersionRepository(session),
        projects=projects,
        node_types=NodeTypeService(),
        audit=audit,
    )


WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]


def get_workflow_controller(service: WorkflowServiceDep) -> WorkflowController:
    return WorkflowController(service)


WorkflowControllerDep = Annotated[WorkflowController, Depends(get_workflow_controller)]
