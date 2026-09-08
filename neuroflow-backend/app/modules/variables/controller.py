"""Variable orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1.

Authorization is a plain role comparison against the organization (any
member reads; non-viewers write) -- the same judgment call
`ProjectService`'s docstring makes for the same reason: nothing else needs
a dedicated `Permission` enum member yet.
"""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.exceptions import PermissionError as AppPermissionError
from app.core.permissions import Role
from app.modules.organizations.service import OrganizationService
from app.modules.variables.models import Variable
from app.modules.variables.schemas import VariableCreate, VariableRead, VariableUpdate
from app.modules.variables.service import VariableService


def _require_write_role(role: Role) -> None:
    if role == Role.VIEWER:
        raise AppPermissionError("Viewers cannot modify variables")


def _to_read(row: Variable) -> VariableRead:
    return VariableRead.model_validate(row)


class VariableController:
    def __init__(self, service: VariableService, organizations: OrganizationService) -> None:
        self._service = service
        self._organizations = organizations

    async def list_for_org(
        self, ctx: RequestContext, organization_id: UUID, *, project_id: UUID | None
    ) -> list[VariableRead]:
        await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        rows = await self._service.list_visible(
            organization_id=organization_id, project_id=project_id
        )
        return [_to_read(row) for row in rows]

    async def create(
        self, ctx: RequestContext, organization_id: UUID, payload: VariableCreate
    ) -> VariableRead:
        role = await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        row = await self._service.create(
            organization_id=organization_id,
            project_id=payload.project_id,
            key=payload.key,
            value=payload.value,
            is_secret=payload.is_secret,
        )
        return _to_read(row)

    async def update(
        self, ctx: RequestContext, variable_id: UUID, payload: VariableUpdate
    ) -> VariableRead:
        variable = await self._service.get(variable_id)
        role = await self._organizations.get_role_for_member(
            organization_id=variable.organization_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        variable = await self._service.update(
            variable=variable, value=payload.value, is_secret=payload.is_secret
        )
        return _to_read(variable)

    async def delete(self, ctx: RequestContext, variable_id: UUID) -> None:
        variable = await self._service.get(variable_id)
        role = await self._organizations.get_role_for_member(
            organization_id=variable.organization_id, user_id=ctx.user_id
        )
        _require_write_role(role)
        await self._service.delete(variable)
