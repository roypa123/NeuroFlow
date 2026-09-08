"""SQL access for credentials. No business rules, no decryption -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import EncryptedBlob
from app.modules.credentials.models import Credential


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        name: str,
        type_: str,
        blob: EncryptedBlob,
        created_by: UUID | None,
    ) -> Credential:
        credential = Credential(
            project_id=project_id,
            name=name,
            type=type_,
            encrypted_data=blob.ciphertext,
            encrypted_dek=blob.encrypted_dek,
            nonce=blob.nonce,
            key_version=blob.key_version,
            created_by=created_by,
        )
        self._session.add(credential)
        await self._session.flush()
        return credential

    async def get_by_id(self, credential_id: UUID) -> Credential | None:
        stmt = select(Credential).where(
            Credential.id == credential_id, Credential.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self, *, project_id: UUID, type_: str | None
    ) -> list[Credential]:
        stmt = select(Credential).where(
            Credential.project_id == project_id, Credential.deleted_at.is_(None)
        )
        if type_ is not None:
            stmt = stmt.where(Credential.type == type_)
        stmt = stmt.order_by(Credential.created_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, credential: Credential, *, name: str | None, blob: EncryptedBlob | None
    ) -> None:
        if name is not None:
            credential.name = name
        if blob is not None:
            credential.encrypted_data = blob.ciphertext
            credential.encrypted_dek = blob.encrypted_dek
            credential.nonce = blob.nonce
            credential.key_version = blob.key_version
        await self._session.flush()

    async def set_oauth_expiry(
        self, credential: Credential, *, expires_at: datetime | None
    ) -> None:
        credential.oauth_expires_at = expires_at
        await self._session.flush()

    async def record_test(
        self, credential: Credential, *, status: str, at: datetime
    ) -> None:
        credential.test_status = status
        credential.last_tested_at = at
        await self._session.flush()

    async def soft_delete(self, credential: Credential, *, at: datetime) -> None:
        credential.deleted_at = at
        await self._session.flush()
