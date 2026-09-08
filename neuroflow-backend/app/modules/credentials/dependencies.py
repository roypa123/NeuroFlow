"""DI wiring for the credentials module. See docs/08-backend-architecture.md
#8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.redis import get_redis
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.credentials.controller import CredentialController
from app.modules.credentials.repository import CredentialRepository
from app.modules.credentials.service import CredentialService
from app.modules.projects.dependencies import ProjectServiceDep
from app.modules.projects.repository import ProjectRepository

RedisDep = Annotated[Redis, Depends(get_redis)]


def get_credential_service(
    session: SessionDep, projects: ProjectServiceDep, redis: RedisDep
) -> CredentialService:
    audit = AuditService(AuditRepository(session))
    return CredentialService(
        credentials=CredentialRepository(session),
        projects=projects,
        project_repository=ProjectRepository(session),
        audit=audit,
        redis=redis,
        master_key=get_settings().credential_master_key.get_secret_value(),
    )


CredentialServiceDep = Annotated[CredentialService, Depends(get_credential_service)]


def get_credential_controller(service: CredentialServiceDep) -> CredentialController:
    return CredentialController(service)


CredentialControllerDep = Annotated[
    CredentialController, Depends(get_credential_controller)
]
