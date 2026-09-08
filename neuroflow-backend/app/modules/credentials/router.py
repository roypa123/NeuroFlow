"""Credential routes: declarations only. Endpoint set mirrors
docs/11-api-design.md #11.10.

`POST /credentials/oauth/callback` takes a JSON body rather than the doc's
literal `GET .../oauth/callback` -- the OAuth `redirect_uri` points at a
frontend route (`OAuthCallbackPage`), which reads `code`/`state` off the
URL and calls this endpoint itself. That keeps the token exchange on the
authenticated API client instead of requiring the backend to render an
HTML confirmation page for an unauthenticated browser redirect. It is
declared before `/{credential_id}` so "oauth" is never matched as a
credential id.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import RequestContextDep
from app.modules.credentials.dependencies import CredentialControllerDep
from app.modules.credentials.schemas import (
    CredentialCreate,
    CredentialRead,
    CredentialTestResult,
    CredentialUpdate,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
)
from app.modules.credentials.types import CredentialTypeDescriptor

router = APIRouter(prefix="/credentials", tags=["credentials"])
credential_types_router = APIRouter(tags=["credentials"])

ProjectIdQuery = Annotated[UUID, Query(alias="projectId")]


@credential_types_router.get("/credential-types", response_model=list[CredentialTypeDescriptor])
async def list_credential_types(
    controller: CredentialControllerDep,
) -> list[CredentialTypeDescriptor]:
    return controller.list_types()


@credential_types_router.get(
    "/credential-types/{key}", response_model=CredentialTypeDescriptor
)
async def get_credential_type(
    key: str, controller: CredentialControllerDep
) -> CredentialTypeDescriptor:
    return controller.get_type(key)


@router.post("/oauth/callback", response_model=CredentialRead)
async def complete_oauth(
    payload: OAuthCallbackRequest, controller: CredentialControllerDep
) -> CredentialRead:
    return await controller.complete_oauth(payload)


@router.get("", response_model=list[CredentialRead])
async def list_credentials(
    ctx: RequestContextDep,
    controller: CredentialControllerDep,
    project_id: ProjectIdQuery,
    type: str | None = None,  # noqa: A002 - matches the query param name
) -> list[CredentialRead]:
    return await controller.list_for_project(ctx, project_id, type_=type)


@router.post("", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    payload: CredentialCreate, ctx: RequestContextDep, controller: CredentialControllerDep
) -> CredentialRead:
    return await controller.create(ctx, payload)


@router.get("/{credential_id}", response_model=CredentialRead)
async def get_credential(
    credential_id: UUID, ctx: RequestContextDep, controller: CredentialControllerDep
) -> CredentialRead:
    return await controller.get(ctx, credential_id)


@router.patch("/{credential_id}", response_model=CredentialRead)
async def update_credential(
    credential_id: UUID,
    payload: CredentialUpdate,
    ctx: RequestContextDep,
    controller: CredentialControllerDep,
) -> CredentialRead:
    return await controller.update(ctx, credential_id, payload)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: UUID, ctx: RequestContextDep, controller: CredentialControllerDep
) -> None:
    await controller.delete(ctx, credential_id)


@router.post("/{credential_id}/test", response_model=CredentialTestResult)
async def test_credential(
    credential_id: UUID, ctx: RequestContextDep, controller: CredentialControllerDep
) -> CredentialTestResult:
    return await controller.test(ctx, credential_id)


@router.get("/{credential_id}/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def start_oauth(
    credential_id: UUID,
    ctx: RequestContextDep,
    controller: CredentialControllerDep,
    redirect_uri: Annotated[str, Query(alias="redirectUri")],
) -> OAuthAuthorizeResponse:
    return await controller.start_oauth(ctx, credential_id, redirect_uri)
