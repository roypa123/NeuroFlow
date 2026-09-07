"""Auth routes: declarations only -- see docs/08-backend-architecture.md
#8.1. Endpoint set mirrors docs/11-api-design.md #11.5.

Not implemented yet, and structurally out of scope until they exist:
`logout-all`, `change-password`, `PATCH /me` -- and rate limiting on
login/register/forgot-password (#11.5's table). None of the frontend's
current auth pages call them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.api.deps import RequestContextDep
from app.core.config import get_settings
from app.modules.auth.dependencies import AuthControllerDep
from app.modules.auth.exceptions import InvalidRefreshTokenError
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# The refresh token travels only as an HttpOnly cookie, scoped to the one
# path prefix that ever reads it -- never in a JSON body. See
# docs/11-api-design.md #11.5 and docs/15-security-and-credentials.md #15.2.
_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=_REFRESH_COOKIE_NAME)]


def _set_refresh_cookie(
    response: Response, *, token: str, expires_at: datetime
) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        # Local dev serves the API over plain http -- a Secure cookie would
        # silently never be sent. Every deployed environment is https.
        secure=settings.is_production,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
        expires=expires_at,
    )


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest, response: Response, controller: AuthControllerDep
) -> LoginResponse:
    result, session = await controller.register(
        email=payload.email, password=payload.password, name=payload.name
    )
    _set_refresh_cookie(
        response,
        token=session.refresh_token,
        expires_at=session.refresh_token_expires_at,
    )
    return result


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, response: Response, controller: AuthControllerDep
) -> LoginResponse:
    result, session = await controller.login(
        email=payload.email, password=payload.password
    )
    _set_refresh_cookie(
        response,
        token=session.refresh_token,
        expires_at=session.refresh_token_expires_at,
    )
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    controller: AuthControllerDep,
    refresh_token: RefreshCookie = None,
) -> TokenResponse:
    if refresh_token is None:
        raise InvalidRefreshTokenError("Refresh token is invalid or expired")
    result, session = await controller.refresh(refresh_token=refresh_token)
    _set_refresh_cookie(
        response,
        token=session.refresh_token,
        expires_at=session.refresh_token_expires_at,
    )
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    controller: AuthControllerDep,
    refresh_token: RefreshCookie = None,
) -> None:
    if refresh_token is not None:
        await controller.logout(refresh_token=refresh_token)
    response.delete_cookie(_REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserRead)
async def me(ctx: RequestContextDep, controller: AuthControllerDep) -> UserRead:
    return await controller.me(ctx.user_id)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest, controller: AuthControllerDep
) -> None:
    # Always 202 regardless of whether the email exists -- see
    # docs/15-security-and-credentials.md #15.2 (no user enumeration).
    # The reset token is created and logged, not emailed: there is no
    # outbound email infra in this codebase yet.
    await controller.forgot_password(email=payload.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    payload: ResetPasswordRequest, controller: AuthControllerDep
) -> None:
    await controller.reset_password(
        token=payload.token, new_password=payload.new_password
    )
