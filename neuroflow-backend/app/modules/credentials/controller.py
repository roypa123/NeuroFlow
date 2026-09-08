"""Credential orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.permissions import Permission, require
from app.modules.credentials.exceptions import CredentialTypeNotFoundError
from app.modules.credentials.models import Credential
from app.modules.credentials.schemas import (
    CredentialCreate,
    CredentialRead,
    CredentialTestResult,
    CredentialUpdate,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
)
from app.modules.credentials.service import CredentialService
from app.modules.credentials.types import CredentialTypeDescriptor, list_credential_types


def _to_read(credential: Credential) -> CredentialRead:
    return CredentialRead.model_validate(credential)


class CredentialController:
    def __init__(self, service: CredentialService) -> None:
        self._service = service

    def list_types(self) -> list[CredentialTypeDescriptor]:
        return list_credential_types()

    def get_type(self, key: str) -> CredentialTypeDescriptor:
        for descriptor in list_credential_types():
            if descriptor.key == key:
                return descriptor
        raise CredentialTypeNotFoundError(f"Unknown credential type: {key}")

    async def list_for_project(
        self, ctx: RequestContext, project_id: UUID, *, type_: str | None
    ) -> list[CredentialRead]:
        rows, role = await self._service.list_for_project(
            project_id=project_id, user_id=ctx.user_id, type_=type_
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        return [_to_read(row) for row in rows]

    async def create(
        self, ctx: RequestContext, payload: CredentialCreate
    ) -> CredentialRead:
        role = await self._service.get_role_for_project(
            project_id=payload.project_id, user_id=ctx.user_id
        )
        require(role, Permission.CREDENTIAL_WRITE, scopes=ctx.scopes)
        credential = await self._service.create(
            project_id=payload.project_id,
            name=payload.name,
            type_=payload.type,
            data=payload.data,
            actor_id=ctx.user_id,
        )
        return _to_read(credential)

    async def get(self, ctx: RequestContext, credential_id: UUID) -> CredentialRead:
        credential, _project, role = await self._service.get(
            credential_id=credential_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_READ, scopes=ctx.scopes)
        return _to_read(credential)

    async def update(
        self, ctx: RequestContext, credential_id: UUID, payload: CredentialUpdate
    ) -> CredentialRead:
        credential, project, role = await self._service.get(
            credential_id=credential_id, user_id=ctx.user_id
        )
        require(role, Permission.CREDENTIAL_WRITE, scopes=ctx.scopes)
        credential = await self._service.update(
            credential=credential,
            name=payload.name,
            data=payload.data,
            actor_id=ctx.user_id,
            organization_id=project.organization_id,
        )
        return _to_read(credential)

    async def delete(self, ctx: RequestContext, credential_id: UUID) -> None:
        credential, project, role = await self._service.get(
            credential_id=credential_id, user_id=ctx.user_id
        )
        require(role, Permission.CREDENTIAL_WRITE, scopes=ctx.scopes)
        await self._service.delete(
            credential=credential, actor_id=ctx.user_id, organization_id=project.organization_id
        )

    async def test(
        self, ctx: RequestContext, credential_id: UUID
    ) -> CredentialTestResult:
        credential, project, role = await self._service.get(
            credential_id=credential_id, user_id=ctx.user_id
        )
        require(role, Permission.CREDENTIAL_WRITE, scopes=ctx.scopes)
        ok, message = await self._service.test(
            credential=credential, actor_id=ctx.user_id, organization_id=project.organization_id
        )
        return CredentialTestResult(ok=ok, message=message)

    async def start_oauth(
        self, ctx: RequestContext, credential_id: UUID, redirect_uri: str
    ) -> OAuthAuthorizeResponse:
        credential, _project, role = await self._service.get(
            credential_id=credential_id, user_id=ctx.user_id
        )
        require(role, Permission.CREDENTIAL_WRITE, scopes=ctx.scopes)
        url = await self._service.start_oauth(
            credential=credential, redirect_uri=redirect_uri
        )
        return OAuthAuthorizeResponse(authorization_url=url)

    async def complete_oauth(self, payload: OAuthCallbackRequest) -> CredentialRead:
        # No RequestContext: this is the provider's own browser redirect
        # back to our callback, not a Bearer-authenticated API call -- see
        # CredentialService.complete_oauth's docstring note.
        credential = await self._service.complete_oauth(
            state=payload.state, code=payload.code
        )
        return _to_read(credential)
