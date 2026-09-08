"""Redis key/channel naming for execution pub/sub and cooperative
cancellation -- shared between `app.engine` (the publisher/checker, worker
-only) and `app.modules.executions` (the API's `/stream` and `/cancel`
endpoints), so the API can interoperate with the engine purely over Redis
without ever importing `app.engine` -- see the import-linter contract in
`pyproject.toml` and this phase's plan finding #1.
"""
from __future__ import annotations

from uuid import UUID


def channel_name(execution_id: UUID) -> str:
    return f"exec:{execution_id}"


def cancel_key(execution_id: UUID) -> str:
    return f"execution:{execution_id}:cancel"
