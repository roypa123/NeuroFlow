"""Credential business rules. Framework-agnostic -- raises AppError
subclasses, never HTTPException. See docs/08-backend-architecture.md #8.1
and docs/09-domain-modules.md #9.6.

`get_decrypted` -- the one method the docs single out as the most
dangerous in the codebase, used to inject a live secret into a running
workflow node -- deliberately does NOT live here. It lives in
`app.modules.credentials.decryption`, importable only by `app.engine` (see
the import-linter contract in pyproject.toml). `test()`/`start_oauth()`/
`complete_oauth()` below decrypt too, but for a narrower, still-audited
purpose (proving a credential the caller just configured actually works,
or completing that same caller's own OAuth handshake) -- they use
`app.core.crypto` directly, a leaf with no import-boundary restriction,
exactly as docs/09-domain-modules.md #9.6 lists them as ordinary
`CredentialService` methods, distinct from `get_decrypted`.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from redis.asyncio import Redis

from app.core.crypto import EncryptedBlob, decrypt_credential, encrypt_credential
from app.core.permissions import Role
from app.modules.audit.service import AuditService
from app.modules.credentials.exceptions import (
    CredentialNotFoundError,
    CredentialOAuthError,
    CredentialTypeNotFoundError,
)
from app.modules.credentials.models import Credential
from app.modules.credentials.oauth import (
    build_authorization_url,
    exchange_code_for_token,
)
from app.modules.credentials.repository import CredentialRepository
from app.modules.credentials.type_registry import (
    get_credential_type,
    render_credential_template,
)
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.service import ProjectService

_OAUTH_STATE_TTL_SECONDS = 600
_OAUTH_STATE_KEY = "oauth:state:{state}"


class CredentialService:
    def __init__(
        self,
        credentials: CredentialRepository,
        projects: ProjectService,
        project_repository: ProjectRepository,
        audit: AuditService,
        redis: Redis,
        master_key: str,
    ) -> None:
        self._credentials = credentials
        self._projects = projects
        self._project_repository = project_repository
        self._audit = audit
        self._redis = redis
        self._master_key = master_key

    async def get(
        self, *, credential_id: UUID, user_id: UUID
    ) -> tuple[Credential, Project, Role]:
        credential = await self._credentials.get_by_id(credential_id)
        if credential is None:
            raise CredentialNotFoundError("Credential not found")
        project, role = await self._projects.get(
            project_id=credential.project_id, user_id=user_id
        )
        return credential, project, role

    async def get_role_for_project(self, *, project_id: UUID, user_id: UUID) -> Role:
        _project, role = await self._projects.get(
            project_id=project_id, user_id=user_id
        )
        return role

    async def list_for_project(
        self, *, project_id: UUID, user_id: UUID, type_: str | None
    ) -> tuple[list[Credential], Role]:
        role = await self.get_role_for_project(project_id=project_id, user_id=user_id)
        rows = await self._credentials.list_by_project(
            project_id=project_id, type_=type_
        )
        return rows, role

    def _require_type(self, type_: str) -> None:
        if get_credential_type(type_) is None:
            raise CredentialTypeNotFoundError(f"Unknown credential type: {type_}")

    async def create(
        self,
        *,
        project_id: UUID,
        name: str,
        type_: str,
        data: dict[str, Any],
        actor_id: UUID,
    ) -> Credential:
        self._require_type(type_)
        project, _role = await self._projects.get(
            project_id=project_id, user_id=actor_id
        )
        blob = encrypt_credential(data, self._master_key)
        credential = await self._credentials.create(
            project_id=project_id,
            name=name,
            type_=type_,
            blob=blob,
            created_by=actor_id,
        )
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="credential.created",
            resource_type="credential",
            resource_id=credential.id,
            changes={"name": name, "type": type_},
        )
        return credential

    async def update(
        self,
        *,
        credential: Credential,
        name: str | None,
        data: dict[str, Any] | None,
        actor_id: UUID,
        organization_id: UUID,
    ) -> Credential:
        blob = None
        if data is not None:
            # Omitted fields are left unchanged: merge onto the existing
            # decrypted data rather than replacing it outright -- see
            # docs/11-api-design.md #11.10.
            existing = decrypt_credential(_blob_of(credential), self._master_key)
            existing.update(data)
            blob = encrypt_credential(existing, self._master_key)
        await self._credentials.update(credential, name=name, blob=blob)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="credential.updated",
            resource_type="credential",
            resource_id=credential.id,
            changes={"name": name} if name else None,
        )
        return credential

    async def delete(
        self, *, credential: Credential, actor_id: UUID, organization_id: UUID
    ) -> None:
        await self._credentials.soft_delete(credential, at=datetime.now(UTC))
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="credential.deleted",
            resource_type="credential",
            resource_id=credential.id,
        )

    async def test(
        self, *, credential: Credential, actor_id: UUID, organization_id: UUID
    ) -> tuple[bool, str | None]:
        descriptor = get_credential_type(credential.type)
        if descriptor is None or descriptor.test is None:
            return True, "No connection test configured for this credential type."
        data = decrypt_credential(_blob_of(credential), self._master_key)
        url = render_credential_template(descriptor.test.url, data)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(descriptor.test.method, url)
            ok = response.is_success
            message = None if ok else f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            ok, message = False, str(exc)
        await self._credentials.record_test(
            credential, status="ok" if ok else "error", at=datetime.now(UTC)
        )
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="credential.tested",
            resource_type="credential",
            resource_id=credential.id,
            changes={"result": "ok" if ok else "error"},
        )
        return ok, message

    async def start_oauth(self, *, credential: Credential, redirect_uri: str) -> str:
        descriptor = get_credential_type(credential.type)
        if descriptor is None or descriptor.oauth is None:
            raise CredentialOAuthError("Credential type does not support OAuth2")
        data = decrypt_credential(_blob_of(credential), self._master_key)
        state = secrets.token_urlsafe(32)
        await self._redis.set(
            _OAUTH_STATE_KEY.format(state=state),
            json.dumps(
                {"credentialId": str(credential.id), "redirectUri": redirect_uri}
            ),
            ex=_OAUTH_STATE_TTL_SECONDS,
        )
        return build_authorization_url(
            authorization_url=data["authorizationUrl"],
            client_id=data["clientId"],
            redirect_uri=redirect_uri,
            scope=data.get("scope", descriptor.oauth.scope),
            state=state,
        )

    async def complete_oauth(self, *, state: str, code: str) -> Credential:
        # No RequestContext here: the provider's browser redirect back to
        # our callback carries no Authorization header, so actor/org are
        # resolved from the credential itself (found via the state token,
        # a cryptographically random value only this service ever handed
        # out) rather than from an authenticated caller.
        key = _OAUTH_STATE_KEY.format(state=state)
        raw = await self._redis.get(key)
        if raw is None:
            raise CredentialOAuthError("OAuth state expired or invalid")
        await self._redis.delete(key)
        payload = json.loads(raw)
        credential = await self._credentials.get_by_id(UUID(payload["credentialId"]))
        if credential is None:
            raise CredentialNotFoundError("Credential not found")

        data = decrypt_credential(_blob_of(credential), self._master_key)
        try:
            token_response = await exchange_code_for_token(
                token_url=data["tokenUrl"],
                client_id=data["clientId"],
                client_secret=data["clientSecret"],
                code=code,
                redirect_uri=payload["redirectUri"],
            )
        except httpx.HTTPError as exc:
            raise CredentialOAuthError(f"Token exchange failed: {exc}") from exc

        data["accessToken"] = token_response.get("access_token")
        if token_response.get("refresh_token"):
            data["refreshToken"] = token_response["refresh_token"]
        blob = encrypt_credential(data, self._master_key)
        await self._credentials.update(credential, name=None, blob=blob)

        expires_in = token_response.get("expires_in")
        if isinstance(expires_in, int | float):
            await self._credentials.set_oauth_expiry(
                credential, expires_at=datetime.now(UTC) + timedelta(seconds=expires_in)
            )

        project = await self._project_repository.get_by_id(credential.project_id)
        if project is not None:
            await self._audit.record(
                organization_id=project.organization_id,
                actor_id=credential.created_by,
                action="credential.oauth_completed",
                resource_type="credential",
                resource_id=credential.id,
            )
        return credential


def _blob_of(credential: Credential) -> EncryptedBlob:
    return EncryptedBlob(
        ciphertext=credential.encrypted_data,
        encrypted_dek=credential.encrypted_dek,
        nonce=credential.nonce,
        key_version=credential.key_version,
    )
