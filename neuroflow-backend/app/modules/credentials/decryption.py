"""Credential decryption -- the single, audited path to plaintext secret
data. See docs/09-domain-modules.md #9.6 and docs/15-security-and-
credentials.md #15.5.

Deliberately its own leaf submodule. The import-linter contract in
pyproject.toml forbids `app.api`/`app.main` from importing this specific
module (while the rest of `app.modules.credentials` -- create/list/test --
stays router-reachable, since none of it returns plaintext). Only
`app.engine` calls this, immediately before a node runs that declared a
credential requirement, and every call is audited -- see this phase's plan
finding #1 and `tests/unit/test_credential_boundary.py`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import EncryptedBlob, decrypt_credential
from app.modules.audit.service import AuditService
from app.modules.credentials.exceptions import CredentialNotFoundError
from app.modules.credentials.repository import CredentialRepository


async def get_decrypted_credential(
    credential_id: UUID,
    *,
    session: AsyncSession,
    audit: AuditService,
    organization_id: UUID,
    execution_id: UUID | None = None,
) -> dict[str, Any]:
    """WORKER ONLY -- the most dangerous function in the codebase. Returns
    the plaintext credential data dict."""
    repo = CredentialRepository(session)
    credential = await repo.get_by_id(credential_id)
    if credential is None:
        raise CredentialNotFoundError("Credential not found")
    data = decrypt_credential(
        EncryptedBlob(
            ciphertext=credential.encrypted_data,
            encrypted_dek=credential.encrypted_dek,
            nonce=credential.nonce,
            key_version=credential.key_version,
        ),
        get_settings().credential_master_key.get_secret_value(),
    )
    await audit.record(
        organization_id=organization_id,
        actor_id=None,
        action="credential.decrypted",
        resource_type="credential",
        resource_id=credential.id,
        changes={"executionId": str(execution_id)} if execution_id else None,
    )
    return data
