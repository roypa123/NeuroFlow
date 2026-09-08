"""Variable business rules. Framework-agnostic -- raises AppError
subclasses, never HTTPException. See docs/08-backend-architecture.md #8.1
and docs/09-domain-modules.md #9.13.

Decrypting a secret variable's value for actual use in `$vars` (finishing
the deferral Phase 4 explicitly left open) lives in
`app.modules.variables.decryption`, not here -- same reasoning, and the
same import-linter enforcement, as `app.modules.credentials.decryption`.
"""
from __future__ import annotations

from uuid import UUID

from app.core.crypto import encrypt_credential
from app.modules.variables.exceptions import VariableNotFoundError
from app.modules.variables.models import Variable
from app.modules.variables.repository import VariableRepository


class VariableService:
    def __init__(self, repository: VariableRepository, master_key: str) -> None:
        self._repository = repository
        self._master_key = master_key

    async def list_visible(
        self, *, organization_id: UUID, project_id: UUID | None
    ) -> list[Variable]:
        return await self._repository.list_visible(
            organization_id=organization_id, project_id=project_id
        )

    async def create(
        self,
        *,
        organization_id: UUID,
        project_id: UUID | None,
        key: str,
        value: str,
        is_secret: bool,
    ) -> Variable:
        blob = encrypt_credential({"value": value}, self._master_key) if is_secret else None
        return await self._repository.create(
            organization_id=organization_id,
            project_id=project_id,
            key=key,
            value=None if is_secret else value,
            blob=blob,
            is_secret=is_secret,
        )

    async def update(
        self, *, variable: Variable, value: str | None, is_secret: bool | None
    ) -> Variable:
        secret = is_secret if is_secret is not None else variable.is_secret
        blob = None
        if secret and value is not None:
            blob = encrypt_credential({"value": value}, self._master_key)
        await self._repository.update(
            variable, value=value, blob=blob, is_secret=is_secret
        )
        return variable

    async def get(self, variable_id: UUID) -> Variable:
        variable = await self._repository.get_by_id(variable_id)
        if variable is None:
            raise VariableNotFoundError("Variable not found")
        return variable

    async def delete(self, variable: Variable) -> None:
        await self._repository.delete(variable)
