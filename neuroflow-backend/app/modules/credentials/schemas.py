"""Pydantic schemas for credentials. See docs/11-api-design.md #11.10.

`CredentialRead` structurally has no field that could ever carry secret
material -- see docs/15-security-and-credentials.md #15.6 item 1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schema import CamelModel


class CredentialRead(CamelModel):
    id: UUID
    project_id: UUID
    name: str
    type: str
    oauth_expires_at: datetime | None
    last_tested_at: datetime | None
    test_status: str | None
    created_at: datetime
    updated_at: datetime


class CredentialCreate(CamelModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    type: str
    data: dict[str, Any]


class CredentialUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    # Omitted fields are left unchanged server-side -- see
    # docs/11-api-design.md #11.10.
    data: dict[str, Any] | None = None


class CredentialTestResult(CamelModel):
    ok: bool
    message: str | None = None


class OAuthAuthorizeResponse(CamelModel):
    authorization_url: str


class OAuthCallbackRequest(CamelModel):
    state: str
    code: str
