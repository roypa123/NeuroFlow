"""Variable decryption -- resolves the `$vars` scope for expression
evaluation. See docs/12-execution-engine.md #12.6 and docs/09-domain-
modules.md #9.13.

A leaf submodule, same pattern and rationale as
`app.modules.credentials.decryption`: only `app.engine` calls this. The
import-linter contract in pyproject.toml forbids `app.api`/`app.main` from
importing it, while the rest of `app.modules.variables` (list/create/
update/delete -- none of which ever return a secret value) stays
router-reachable.
"""

from __future__ import annotations

from uuid import UUID

from app.core.crypto import EncryptedBlob, decrypt_credential
from app.modules.variables.repository import VariableRepository


async def get_vars_snapshot(
    *,
    repository: VariableRepository,
    organization_id: UUID,
    project_id: UUID | None,
    master_key: str,
) -> tuple[dict[str, str], list[str]]:
    """Returns every variable visible to this project (org-wide plus the
    project's own) as a plain `{key: value}` dict, decrypting secret ones,
    plus the list of decrypted values that are secret. The caller
    (`app.engine.context`) registers that second list with the execution's
    `SecretRegistry` before the `$vars` scope is ever exposed to
    expressions/logs -- see docs/15-security-and-credentials.md #15.6.
    """
    rows = await repository.list_visible(
        organization_id=organization_id, project_id=project_id
    )
    result: dict[str, str] = {}
    secret_values: list[str] = []
    for row in rows:
        if not row.is_secret:
            result[row.key] = row.value or ""
            continue
        if (
            row.encrypted_value is None
            or row.encrypted_dek is None
            or row.nonce is None
        ):
            continue
        blob = EncryptedBlob(
            ciphertext=row.encrypted_value,
            encrypted_dek=row.encrypted_dek,
            nonce=row.nonce,
            key_version=row.key_version or 1,
        )
        value = decrypt_credential(blob, master_key).get("value", "")
        result[row.key] = value
        secret_values.append(value)
    return result, secret_values
