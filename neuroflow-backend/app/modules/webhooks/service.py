"""Webhook business rules: registration and HMAC/header signature
verification. See docs/09-domain-modules.md #9.11 and docs/15-security-and-
credentials.md #15.9.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.modules.webhooks.models import WebhookRegistration
from app.modules.webhooks.repository import WebhookRepository

_TEST_TTL_SECONDS = 120
# Verify against the raw body bytes, before JSON parsing, and reject
# anything older than this -- both explicitly called out in docs/15-
# security-and-credentials.md #15.9 as easy to get wrong and both fatal.
_HMAC_TIMESTAMP_TOLERANCE_SECONDS = 300


class WebhookService:
    def __init__(self, repository: WebhookRepository) -> None:
        self._repository = repository

    def build_url(self, *, path: str, is_test: bool) -> str:
        base = get_settings().public_url.rstrip("/")
        segment = "webhook-test" if is_test else "webhook"
        return f"{base}/{segment}/{path}"

    async def register(
        self,
        *,
        workflow_id: UUID,
        node_id: str,
        path: str,
        method: str,
        auth: dict[str, Any] | None,
        response_mode: str,
    ) -> WebhookRegistration:
        return await self._repository.create(
            workflow_id=workflow_id,
            node_id=node_id,
            path=path,
            method=method.upper(),
            auth=auth,
            response_mode=response_mode,
        )

    async def register_test(
        self,
        *,
        workflow_id: UUID,
        node_id: str,
        path: str,
        method: str,
        auth: dict[str, Any] | None,
        response_mode: str,
    ) -> WebhookRegistration:
        return await self._repository.create(
            workflow_id=workflow_id,
            node_id=node_id,
            path=path,
            method=method.upper(),
            auth=auth,
            response_mode=response_mode,
            is_test=True,
            expires_at=datetime.now(UTC) + timedelta(seconds=_TEST_TTL_SECONDS),
        )

    async def unregister(self, workflow_id: UUID) -> None:
        await self._repository.delete_for_workflow(workflow_id)

    async def list_for_workflow(self, workflow_id: UUID) -> list[WebhookRegistration]:
        return await self._repository.list_for_workflow(workflow_id)

    async def find_active(
        self, *, path: str, method: str, is_test: bool
    ) -> WebhookRegistration | None:
        return await self._repository.find_active(
            path=path, method=method.upper(), is_test=is_test, now=datetime.now(UTC)
        )


def auth_spec_from_node_params(parameters: dict[str, Any]) -> dict[str, Any] | None:
    """Maps a Webhook Trigger node's `authMode`/`hmacSecret`/
    `headerAuthValue` parameters onto the `auth` blob stored on its
    registration -- shared by `WorkflowService.activate` (real
    registration) and `WebhookController.listen_for_test` (test
    registration) so the two paths can never disagree on the mapping."""
    mode = parameters.get("authMode", "none")
    if mode in (None, "none"):
        return None
    if mode == "hmac":
        return {"type": "hmac", "secret": parameters.get("hmacSecret", "")}
    if mode == "headerAuth":
        return {"type": "headerAuth", "headerValue": parameters.get("headerAuthValue", "")}
    return None


def verify_signature(
    auth: dict[str, Any] | None,
    *,
    raw_body: bytes,
    headers: dict[str, str],
) -> bool:
    """Returns True if the request satisfies the registration's declared
    auth mode. `auth is None` or `{"type": "none"}` means no verification
    is required."""
    if not auth or auth.get("type", "none") == "none":
        return True
    if auth["type"] == "headerAuth":
        header_name = auth.get("headerName", "Authorization")
        return headers.get(header_name.lower()) == auth.get("headerValue")
    if auth["type"] == "hmac":
        secret = auth.get("secret", "")
        signature_header_name = auth.get("signatureHeader", "x-webhook-signature")
        timestamp_header_name = auth.get("timestampHeader", "x-webhook-timestamp")
        signature = headers.get(signature_header_name.lower())
        timestamp = headers.get(timestamp_header_name.lower())
        if signature is None:
            return False
        if timestamp is not None:
            try:
                if abs(time.time() - int(timestamp)) > _HMAC_TIMESTAMP_TOLERANCE_SECONDS:
                    return False
            except ValueError:
                return False
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    return False
