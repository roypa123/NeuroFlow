"""Request/response schemas for auth. Mirrors docs/11-api-design.md #11.5
and neuroflow-frontend/src/types/auth.ts exactly -- the two must be kept in
sync by hand since there is no shared schema generation yet."""
from __future__ import annotations

from pydantic import EmailStr, Field

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
