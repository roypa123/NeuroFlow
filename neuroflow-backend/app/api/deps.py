"""Shared FastAPI dependencies: the DB session, and the RequestContext every
controller authorizes against.

RequestContext is deliberately a plain dataclass with no FastAPI types in
it, so the same shape can be constructed by hand in the worker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import AppError
from app.core.permissions import Role
from app.core.security import decode_access_token


@dataclass(slots=True, frozen=True)
class RequestContext:
    user_id: UUID
    org_id: UUID | None
    role: Role | None
    request_id: str | None = None


class Unauthorized(AppError):
    code = "unauthorized"
    http_status = 401


async def get_request_context(
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired token") from exc

    role_value = payload.get("role")
    return RequestContext(
        user_id=UUID(payload["sub"]),
        org_id=UUID(payload["org"]) if payload.get("org") else None,
        role=Role(role_value) if role_value else None,
    )


SessionDep = Annotated[AsyncSession, Depends(get_session)]
RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
