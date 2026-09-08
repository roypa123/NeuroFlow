"""SQL access for variables. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import EncryptedBlob
from app.modules.variables.models import Variable


class VariableRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        project_id: UUID | None,
        key: str,
        value: str | None,
        blob: EncryptedBlob | None,
        is_secret: bool,
    ) -> Variable:
        row = Variable(
            organization_id=organization_id,
            project_id=project_id,
            key=key,
            value=value,
            encrypted_value=blob.ciphertext if blob else None,
            encrypted_dek=blob.encrypted_dek if blob else None,
            nonce=blob.nonce if blob else None,
            key_version=blob.key_version if blob else None,
            is_secret=is_secret,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_id(self, variable_id: UUID) -> Variable | None:
        stmt = select(Variable).where(Variable.id == variable_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_visible(
        self, *, organization_id: UUID, project_id: UUID | None
    ) -> list[Variable]:
        """Org-wide variables (`project_id IS NULL`) plus this project's
        own -- both are visible to expressions running in the project, per
        docs/09-domain-modules.md #9.13."""
        stmt = select(Variable).where(Variable.organization_id == organization_id)
        if project_id is not None:
            stmt = stmt.where(
                (Variable.project_id == project_id) | (Variable.project_id.is_(None))
            )
        else:
            stmt = stmt.where(Variable.project_id.is_(None))
        result = await self._session.execute(stmt.order_by(Variable.key))
        return list(result.scalars().all())

    async def update(
        self,
        row: Variable,
        *,
        value: str | None,
        blob: EncryptedBlob | None,
        is_secret: bool | None,
    ) -> None:
        if is_secret is not None:
            row.is_secret = is_secret
        if row.is_secret:
            row.value = None
            if blob is not None:
                row.encrypted_value = blob.ciphertext
                row.encrypted_dek = blob.encrypted_dek
                row.nonce = blob.nonce
                row.key_version = blob.key_version
        else:
            row.value = value
            row.encrypted_value = None
            row.encrypted_dek = None
            row.nonce = None
            row.key_version = None
        await self._session.flush()

    async def delete(self, row: Variable) -> None:
        await self._session.delete(row)
        await self._session.flush()
