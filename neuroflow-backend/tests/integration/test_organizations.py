"""Organization/membership business rules that aren't pure tenant
isolation -- RBAC enforcement, the last-owner guard, and invitation
conflicts. See docs/09-domain-modules.md #9.4 and
docs/11-api-design.md #11.6."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from tests.factories import make_actor


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_member_cannot_invite_others(client, db_session: AsyncSession) -> None:
    member = await make_actor(
        db_session, email="member@example.com", org_name="Org", role=Role.MEMBER
    )

    response = await client.post(
        f"/api/v1/organizations/{member.organization.id}/invitations",
        json={"email": "new-hire@example.com", "role": "viewer"},
        headers=_auth(member.token),
    )

    assert response.status_code == 403, response.text


async def test_viewer_cannot_create_a_project(client, db_session: AsyncSession) -> None:
    viewer = await make_actor(
        db_session, email="viewer@example.com", org_name="Org", role=Role.VIEWER
    )

    response = await client.post(
        "/api/v1/projects",
        json={"organizationId": str(viewer.organization.id), "name": "Nope"},
        headers=_auth(viewer.token),
    )

    assert response.status_code == 403, response.text


async def test_removing_the_last_owner_is_rejected(
    client, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner@example.com", org_name="Org", role=Role.OWNER
    )

    response = await client.delete(
        f"/api/v1/organizations/{owner.organization.id}/members/{owner.user.id}",
        headers=_auth(owner.token),
    )

    assert response.status_code == 403, response.text


async def test_demoting_the_last_owner_is_rejected(
    client, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner2@example.com", org_name="Org", role=Role.OWNER
    )

    response = await client.patch(
        f"/api/v1/organizations/{owner.organization.id}/members/{owner.user.id}",
        json={"role": "admin"},
        headers=_auth(owner.token),
    )

    assert response.status_code == 403, response.text


async def test_removing_a_co_owner_is_allowed_when_another_owner_remains(
    client, db_session: AsyncSession
) -> None:
    from app.core.security import create_access_token
    from app.modules.organizations.models import OrganizationMember

    owner_1 = await make_actor(
        db_session, email="owner-1@example.com", org_name="Org", role=Role.OWNER
    )
    owner_2 = await make_actor(
        db_session, email="owner-2@example.com", org_name="Org 2", role=Role.OWNER
    )
    # Add owner_2's user as a SECOND owner of owner_1's organization.
    db_session.add(
        OrganizationMember(
            organization_id=owner_1.organization.id,
            user_id=owner_2.user.id,
            role=Role.OWNER,
        )
    )
    await db_session.flush()
    owner_1_token_for_own_org = create_access_token(
        user_id=owner_1.user.id,
        org_id=owner_1.organization.id,
        role="owner",
        jti="test-fixture-2",
    )

    response = await client.delete(
        f"/api/v1/organizations/{owner_1.organization.id}/members/{owner_2.user.id}",
        headers=_auth(owner_1_token_for_own_org),
    )

    assert response.status_code == 204, response.text


async def test_duplicate_invitation_is_a_conflict(
    client, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner3@example.com", org_name="Org", role=Role.OWNER
    )
    payload = {"email": "invitee@example.com", "role": "member"}

    first = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/invitations",
        json=payload,
        headers=_auth(owner.token),
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/invitations",
        json=payload,
        headers=_auth(owner.token),
    )
    assert second.status_code == 409, second.text


async def test_accepting_an_invitation_sent_to_a_different_email_is_rejected(
    client, db_session: AsyncSession
) -> None:
    owner = await make_actor(
        db_session, email="owner4@example.com", org_name="Org", role=Role.OWNER
    )
    invite = await client.post(
        f"/api/v1/organizations/{owner.organization.id}/invitations",
        json={"email": "intended-recipient@example.com", "role": "member"},
        headers=_auth(owner.token),
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]

    someone_else = await make_actor(
        db_session, email="someone-else@example.com", org_name="Someone Else's Org"
    )

    response = await client.post(
        f"/api/v1/invitations/{token}/accept", headers=_auth(someone_else.token)
    )

    assert response.status_code == 403, response.text
