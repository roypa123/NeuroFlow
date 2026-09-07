"""API key issuance, scope enforcement, and revocation. See
docs/09-domain-modules.md #9.2 and app/core/permissions.py's require()
docstring for the scope-narrowing rule this exercises."""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from tests.factories import make_actor


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_member_cannot_manage_api_keys(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    member = await make_actor(
        db_session, email="member@example.com", org_name="Org", role=Role.MEMBER
    )

    response = await client.post(
        f"/api/v1/organizations/{member.organization.id}/api-keys",
        json={"name": "key", "scopes": ["workflow:read"]},
        headers=_auth(member.token),
    )

    assert response.status_code == 403, response.text


async def test_owner_can_issue_list_and_revoke_a_key(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner@example.com", org_name="Org", role=Role.OWNER
    )

    created = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/api-keys",
        json={"name": "CI key", "scopes": ["workflow:read"]},
        headers=_auth(owner.token),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["key"].startswith("nf_live_")
    key_id = body["id"]

    listed = await client.get(
        f"/api/v1/organizations/{owner.organization.id}/api-keys",
        headers=_auth(owner.token),
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert "key" not in listed.json()[0]

    revoked = await client.delete(
        f"/api/v1/organizations/{owner.organization.id}/api-keys/{key_id}",
        headers=_auth(owner.token),
    )
    assert revoked.status_code == 204, revoked.text

    listed_again = await client.get(
        f"/api/v1/organizations/{owner.organization.id}/api-keys",
        headers=_auth(owner.token),
    )
    assert listed_again.json() == []


async def test_scoped_api_key_authenticates_but_cannot_exceed_its_scopes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner2@example.com", org_name="Org", role=Role.OWNER
    )
    created = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/api-keys",
        json={"name": "read-only key", "scopes": ["workflow:read"]},
        headers=_auth(owner.token),
    )
    raw_key = created.json()["key"]

    # A read-scoped key can authenticate a normal request...
    members = await client.get(
        f"/api/v1/organizations/{owner.organization.id}/members", headers=_auth(raw_key)
    )
    assert members.status_code == 200, members.text

    # ...but is rejected for member:manage, even though the key's OWNER
    # (an org owner) would normally be allowed -- the scope narrows what
    # the key itself can do below what its owner's role permits.
    invite = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/invitations",
        json={"email": "someone@example.com", "role": "viewer"},
        headers=_auth(raw_key),
    )
    assert invite.status_code == 403, invite.text
