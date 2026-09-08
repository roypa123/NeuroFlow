"""DI wiring for the executions module. See docs/08-backend-architecture.md
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
from app.modules.executions.controller import ExecutionController
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.executions.service import ExecutionService
from app.modules.workflows.dependencies import WorkflowServiceDep
from app.modules.workflows.repository import WorkflowVersionRepository

RedisDep = Annotated[Redis, Depends(get_redis)]
ArqPoolDep = Annotated[ArqRedis, Depends(get_arq_pool)]


def get_execution_service(
    session: SessionDep,
    workflows: WorkflowServiceDep,
    redis: RedisDep,
    queue: ArqPoolDep,
) -> ExecutionService:
    # AuditService is built directly here, matching the pattern already
    # established in workflows/dependencies.py.
    audit = AuditService(AuditRepository(session))
    return ExecutionService(
        executions=ExecutionRepository(session),
        node_executions=NodeExecutionRepository(session),
        execution_data=ExecutionDataRepository(session),
        workflows=workflows,
        audit=audit,
        redis=redis,
        queue=queue,
    )


ExecutionServiceDep = Annotated[ExecutionService, Depends(get_execution_service)]


def get_execution_controller(
    service: ExecutionServiceDep, session: SessionDep, redis: RedisDep
) -> ExecutionController:
    return ExecutionController(service, WorkflowVersionRepository(session), redis)


ExecutionControllerDep = Annotated[ExecutionController, Depends(get_execution_controller)]
