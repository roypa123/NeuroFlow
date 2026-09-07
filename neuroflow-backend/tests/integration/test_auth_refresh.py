"""Refresh token rotation and reuse detection. See
docs/09-domain-modules.md #9.2: "Refresh tokens rotate on every use;
presenting an already-used token revokes the whole family."

This exercises AuthService.refresh()'s reuse branch specifically because
it once had a real bug: the revocation was rolled back by the very
rejection it caused, since it shared the request's own session and
get_session() rolls back on any raised exception. See
RefreshTokenRepository.commit()'s docstring for the fix.
"""
from __future__ import annotations

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Test User", "password": "TestPass123!"},
    )
    assert response.status_code == 201, response.text


async def test_replaying_a_rotated_refresh_token_revokes_the_whole_family(
    client: AsyncClient,
) -> None:
    await _register(client, "refresh-reuse@example.com")
    original_cookie = client.cookies.get("refresh_token")
    assert original_cookie

    first_refresh = await client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200, first_refresh.text
    rotated_cookie = client.cookies.get("refresh_token")
    assert rotated_cookie
    assert rotated_cookie != original_cookie

    # Replaying the now-stale original cookie must be rejected...
    client.cookies.set("refresh_token", original_cookie)
    replay_response = await client.post("/api/v1/auth/refresh")
    assert replay_response.status_code == 401, replay_response.text

    # ...and must burn the ENTIRE family: the legitimately-rotated cookie
    # that replaced it stops working too.
    client.cookies.set("refresh_token", rotated_cookie)
    legit_response = await client.post("/api/v1/auth/refresh")
    assert legit_response.status_code == 401, legit_response.text


async def test_a_single_refresh_without_replay_works_normally(
    client: AsyncClient,
) -> None:
    await _register(client, "refresh-normal@example.com")

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200, response.text
    body = response.json()
    assert "accessToken" in body
    assert body["tokenType"] == "Bearer"
