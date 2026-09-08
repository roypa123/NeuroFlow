"""DI wiring for the variables module. See docs/08-backend-architecture.md
#8.4."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.modules.organizations.dependencies import OrganizationServiceDep
from app.modules.variables.controller import VariableController
from app.modules.variables.repository import VariableRepository
from app.modules.variables.service import VariableService


def get_variable_service(session: SessionDep) -> VariableService:
    return VariableService(
        VariableRepository(session),
        get_settings().credential_master_key.get_secret_value(),
    )


VariableServiceDep = Annotated[VariableService, Depends(get_variable_service)]


def get_variable_controller(
    service: VariableServiceDep, organizations: OrganizationServiceDep
) -> VariableController:
    return VariableController(service, organizations)


VariableControllerDep = Annotated[VariableController, Depends(get_variable_controller)]
