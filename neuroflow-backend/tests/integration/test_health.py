"""Liveness must never check dependencies; readiness must -- see
docs/16-observability.md #16.7. Both are exercised against the real ASGI
app with no database or Redis running, which is exactly the case that
distinguishes the two: liveness must still say ok, readiness must not.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_is_ok_with_no_dependencies_running(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_ready_reports_503_when_dependencies_are_down(
    client: AsyncClient,
) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["database"] == "error"
    assert body["redis"] == "error"


async def test_health_response_carries_a_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "X-Request-Id" in response.headers
