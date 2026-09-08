"""Pydantic schemas for webhooks. See docs/11-api-design.md #11.12."""

from __future__ import annotations

from uuid import UUID

from app.core.schema import CamelModel


class WebhookRegistrationRead(CamelModel):
    id: UUID
    node_id: str
    path: str
    method: str
    is_test: bool
    response_mode: str
    url: str


class TestWebhookRequest(CamelModel):
    node_id: str
