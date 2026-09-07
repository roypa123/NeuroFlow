"""SQL access for refresh and password-reset tokens. No business rules --
see docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import PasswordResetToken, RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: UUID, token_hash: str, family_id: UUID, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Unlike get_active_by_hash, this does NOT filter out revoked
        tokens -- AuthService.refresh() needs to tell "never existed" apart
        from "already used" to detect reuse of a rotated-away token."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, *, at: datetime) -> None:
        token.revoked_at = at

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None)
            )
            .values(revoked_at=at)
        )
        await self._session.execute(stmt)

    async def commit(self) -> None:
        """Escape hatch from "transaction boundary is the request"
        (docs/08-backend-architecture.md #8.4), used in exactly one place:
        AuthService.refresh()'s reuse-detection branch, which is about to
        raise -- and get_session()'s rollback-on-exception would otherwise
        silently undo the revocation that makes the security control
        real. Safe here specifically because nothing else has written
        anything earlier in that same request."""
        await self._session.commit()

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        await self._session.execute(stmt)


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_active_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken, *, at: datetime) -> None:
        token.used_at = at
