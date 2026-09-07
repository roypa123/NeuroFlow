"""Request/response schemas for auth. Mirrors docs/11-api-design.md #11.5
and neuroflow-frontend/src/types/auth.ts exactly -- the two must be kept in
sync by hand since there is no shared schema generation yet."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.core.permissions import Permission
from app.core.schema import CamelModel
from app.modules.users.schemas import UserRead


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(min_length=1, max_length=200)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(CamelModel):
    email: EmailStr


class ResetPasswordRequest(CamelModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)


class TokenResponse(CamelModel):
    access_token: str
    expires_in: int
    token_type: str = "Bearer"  # noqa: S105 -- an auth scheme name, not a secret


class LoginResponse(TokenResponse):
    user: UserRead


class ApiKeyCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[Permission] = Field(min_length=1)
    expires_at: datetime | None = None


class ApiKeyRead(CamelModel):
    id: UUID
    name: str
    prefix: str
    scopes: list[Permission]
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyRead):
    # The raw secret, present ONLY in the response to the create call --
    # ApiKeyRead (returned by list/get) has no field for it at all. Not
    # redacted -- structurally absent, same rationale as CredentialRead
    # per docs/08-backend-architecture.md #8.7.
    key: str
