"""Tenant isolation: the highest-value test file in the repo -- see
docs/17-testing-strategy.md #17.4. A resource in an organization the
caller does not belong to must 404, never 403 (403 confirms it exists).

Every organizations/projects endpoint that takes a resource id is
parameterized here against a caller from a *different* organization.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import Actor, make_actor, make_project, make_workflow


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def two_orgs(db_session: AsyncSession) -> tuple[Actor, Actor, UUID, UUID]:
    owner_a = await make_actor(
        db_session, email="owner-a@example.com", org_name="Org A"
    )
    owner_b = await make_actor(
        db_session, email="owner-b@example.com", org_name="Org B"
    )
    project_b = await make_project(db_session, organization_id=owner_b.organization.id)
    workflow_b = await make_workflow(db_session, project_id=project_b.id)
    return owner_a, owner_b, project_b.id, workflow_b.id


CrossTenantCase = Callable[[UUID, UUID, UUID], tuple[str, str, dict[str, Any] | None]]

CROSS_TENANT_CASES: list[CrossTenantCase] = [
    lambda org_id, _project_id, _workflow_id: ("GET", f"/organizations/{org_id}", None),
    lambda org_id, _project_id, _workflow_id: (
        "PATCH",
        f"/organizations/{org_id}",
        {"name": "Hijacked"},
    ),
    lambda org_id, _project_id, _workflow_id: (
        "GET",
        f"/organizations/{org_id}/members",
        None,
    ),
    lambda org_id, _project_id, _workflow_id: (
        "POST",
        f"/organizations/{org_id}/invitations",
        {"email": "x@example.com", "role": "member"},
    ),
    lambda _org_id, project_id, _workflow_id: ("GET", f"/projects/{project_id}", None),
    lambda _org_id, project_id, _workflow_id: (
        "PATCH",
        f"/projects/{project_id}",
        {"name": "Hijacked"},
    ),
    lambda _org_id, project_id, _workflow_id: (
        "DELETE",
        f"/projects/{project_id}",
        None,
    ),
    lambda _org_id, _project_id, workflow_id: (
        "GET",
        f"/workflows/{workflow_id}",
        None,
    ),
    lambda _org_id, _project_id, workflow_id: (
        "PATCH",
        f"/workflows/{workflow_id}",
        {"name": "Hijacked"},
    ),
    lambda _org_id, _project_id, workflow_id: (
        "DELETE",
        f"/workflows/{workflow_id}",
        None,
    ),
    lambda _org_id, _project_id, workflow_id: (
        "POST",
        f"/workflows/{workflow_id}/activate",
        None,
    ),
    lambda _org_id, _project_id, workflow_id: (
        "GET",
        f"/workflows/{workflow_id}/versions",
        None,
    ),
]


@pytest.mark.parametrize("case", CROSS_TENANT_CASES)
async def test_cross_tenant_access_is_404_not_403(
    client: AsyncClient,
    two_orgs: tuple[Actor, Actor, UUID, UUID],
    case: CrossTenantCase,
) -> None:
    owner_a, owner_b, project_b_id, workflow_b_id = two_orgs
    method, path, body = case(owner_b.organization.id, project_b_id, workflow_b_id)

    response = await client.request(
        method, f"/api/v1{path}", json=body, headers=_auth(owner_a.token)
    )

    assert response.status_code == 404, response.text


async def test_cross_tenant_member_removal_is_404(
    client: AsyncClient,
    two_orgs: tuple[Actor, Actor, UUID, UUID],
    db_session: AsyncSession,
) -> None:
    owner_a, owner_b, _project_b_id, _workflow_b_id = two_orgs
    response = await client.delete(
        f"/api/v1/organizations/{owner_b.organization.id}/members/{owner_b.user.id}",
        headers=_auth(owner_a.token),
    )
    assert response.status_code == 404, response.text


async def test_project_list_only_shows_the_caller_s_own_organization(
    client: AsyncClient,
    two_orgs: tuple[Actor, Actor, UUID, UUID],
    db_session: AsyncSession,
) -> None:
    # make_actor seeds a bare membership, not the full
    # OrganizationService.create_with_owner bootstrap, so Org A starts with
    # no projects until this test adds one -- Org B's project (from the
    # two_orgs fixture) must never appear in Org A's list.
    owner_a, _owner_b, _project_b_id, _workflow_b_id = two_orgs
    await make_project(db_session, organization_id=owner_a.organization.id, name="Mine")

    response = await client.get(
        "/api/v1/projects",
        params={"organizationId": str(owner_a.organization.id)},
        headers=_auth(owner_a.token),
    )
    assert response.status_code == 200, response.text
    assert [p["name"] for p in response.json()] == ["Mine"]
