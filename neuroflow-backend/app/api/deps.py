"""Shared FastAPI dependencies: the DB session, and the RequestContext every
controller authorizes against.

RequestContext is deliberately a plain dataclass with no FastAPI types in
it, so the same shape can be constructed by hand in the worker.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import UnauthorizedError
from app.core.permissions import Permission, Role
from app.core.security import decode_access_token, hash_opaque_token
from app.modules.auth.repository import ApiKeyRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@dataclass(slots=True, frozen=True)
class RequestContext:
    user_id: UUID
    org_id: UUID | None
    role: Role | None
    # None for a JWT-authenticated request: the role above already carries
    # its full permission set, unrestricted. A concrete frozenset for an
    # API-key-authenticated one: an explicit allow-list that can only ever
    # narrow what the key's owner role would otherwise permit -- see
    # app/core/permissions.py's require().
    scopes: frozenset[Permission] | None = None
    request_id: str | None = None


async def _context_from_api_key(token: str, session: AsyncSession) -> RequestContext:
    # Deliberately a direct repository lookup, not app.modules.auth's
    # AuthService: building that service's full dependency graph
    # (OrganizationService -> its own repositories and AuditService) on
    # every single authenticated request just to hash-and-look-up a key
    # would be wasteful, and nothing else here needs any of it.
    repo = ApiKeyRepository(session)
    api_key = await repo.get_active_by_hash(hash_opaque_token(token))
    now = datetime.now(UTC)
    if api_key is None or (api_key.expires_at is not None and api_key.expires_at < now):
        raise UnauthorizedError("Invalid or revoked API key")
    await repo.touch_last_used(api_key, at=now)
    return RequestContext(
        user_id=api_key.user_id,
        org_id=api_key.organization_id,
        role=None,
        scopes=frozenset(Permission(scope) for scope in api_key.scopes),
    )


def _context_from_jwt(token: str) -> RequestContext:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    role_value = payload.get("role")
    return RequestContext(
        user_id=UUID(payload["sub"]),
        org_id=UUID(payload["org"]) if payload.get("org") else None,
        role=Role(role_value) if role_value else None,
    )


async def get_request_context(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1]

    # API keys use a distinctive, non-JWT-shaped prefix (see
    # app/modules/auth/service.py's API_KEY_PREFIX) so the two auth
    # mechanisms never need to be distinguished by trial-and-error parsing.
    if token.startswith("nf_"):
        return await _context_from_api_key(token, session)
    return _context_from_jwt(token)


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
