"""Test data factories: seed a user + organization + membership directly
against a db_session, bypassing the HTTP registration flow, so tenant-
isolation and RBAC tests can set up fixtures in one call. See
docs/17-testing-strategy.md #17.4.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.core.security import create_access_token, hash_password
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.projects.models import Project
from app.modules.users.models import User
from app.modules.workflows.models import Workflow, WorkflowVersion

TEST_PASSWORD = "TestPass123!"  # noqa: S105 -- fixture data, not a real secret


@dataclass(slots=True, frozen=True)
class Actor:
    user: User
    organization: Organization
    role: Role
    token: str


async def make_actor(
    session: AsyncSession, *, email: str, org_name: str, role: Role = Role.OWNER
) -> Actor:
    user = User(
        email=email,
        name=email.split("@", 1)[0],
        password_hash=hash_password(TEST_PASSWORD),
    )
    session.add(user)
    await session.flush()

    organization = Organization(name=org_name)
    session.add(organization)
    await session.flush()

    session.add(
        OrganizationMember(organization_id=organization.id, user_id=user.id, role=role)
    )
    await session.flush()

    token = create_access_token(
        user_id=user.id, org_id=organization.id, role=role.value, jti="test-fixture"
    )
    return Actor(user=user, organization=organization, role=role, token=token)


async def make_project(
    session: AsyncSession, *, organization_id: UUID, name: str = "Test Project"
) -> Project:
    project = Project(organization_id=organization_id, name=name)
    session.add(project)
    await session.flush()
    return project


async def make_workflow(
    session: AsyncSession,
    *,
    project_id: UUID,
    name: str = "Test Workflow",
    graph: dict[str, object] | None = None,
) -> Workflow:
    workflow = Workflow(project_id=project_id, name=name, settings={})
    session.add(workflow)
    await session.flush()
    default_graph = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    version = WorkflowVersion(
        workflow_id=workflow.id,
        version=1,
        graph=graph or default_graph,
        checksum="test-checksum",
    )
    session.add(version)
    await session.flush()
    workflow.active_version_id = version.id
    await session.flush()
    return workflow
