"""DI wiring for the workflows module. See docs/08-backend-architecture.md
#8.4."""
from __future__ import annotations

from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends
from redis.asyncio import Redis

from app.api.deps import SessionDep
from app.core.queue import get_arq_pool
from app.core.redis import get_redis
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.executions.service import ExecutionService
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


def get_workflow_controller(
    service: WorkflowServiceDep,
    session: SessionDep,
    redis: Annotated[Redis, Depends(get_redis)],
    queue: Annotated[ArqRedis, Depends(get_arq_pool)],
) -> WorkflowController:
    # ExecutionService is built directly here (not via
    # executions.dependencies.ExecutionServiceDep) for the same reason
    # AuditService is above: executions.dependencies already imports
    # WorkflowServiceDep, so importing back the other way would cycle.
    audit = AuditService(AuditRepository(session))
    executions = ExecutionService(
        executions=ExecutionRepository(session),
        node_executions=NodeExecutionRepository(session),
        execution_data=ExecutionDataRepository(session),
        workflows=service,
        audit=audit,
        redis=redis,
        queue=queue,
    )
    return WorkflowController(service, executions)


WorkflowControllerDep = Annotated[WorkflowController, Depends(get_workflow_controller)]
