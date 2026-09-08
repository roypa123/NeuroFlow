"""Execution creation, listing, and cancel/retry state transitions. See
docs/09-domain-modules.md #9.9 and docs/11-api-design.md #11.8.

`POST /workflows/{id}/execute` enqueues a real arq job, so -- like
`/health/ready`'s Redis check -- these tests additionally need a reachable
Redis alongside the testcontainers Postgres `tests/conftest.py` already
provides; a worker actually consuming the queue and running the graph to
completion is exercised by the live E2E script for this phase instead
(this pytest harness has no worker process, only the API + DB), matching
the project's established "unit/integration in pytest, live E2E for
things needing a running worker/browser" split.
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from tests.factories import Actor, make_actor, make_project, make_workflow


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_project_owner(db_session: AsyncSession) -> tuple[Actor, str]:
    owner = await make_actor(
        db_session, email="owner@example.com", org_name="Org", role=Role.OWNER
    )
    project = await make_project(db_session, organization_id=owner.organization.id)
    return owner, str(project.id)


_TRIGGER_GRAPH = {
    "nodes": [
        {
            "id": "n1",
            "type": "neuroflow.manualTrigger",
            "position": {"x": 0, "y": 0},
            "parameters": {},
        }
    ],
    "edges": [],
    "viewport": {"x": 0, "y": 0, "zoom": 1},
}


async def test_execute_creates_a_queued_execution(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    workflow = await make_workflow(
        db_session, project_id=project_id, graph=_TRIGGER_GRAPH
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow.id}/execute", headers=_auth(owner.token)
    )

    assert response.status_code == 202, response.text
    execution_id = response.json()["executionId"]

    detail = await client.get(
        f"/api/v1/executions/{execution_id}", headers=_auth(owner.token)
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "queued"
    assert body["mode"] == "manual"
    assert body["workflowId"] == str(workflow.id)


async def test_list_executions_filters_by_workflow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    workflow_a = await make_workflow(
        db_session, project_id=project_id, name="A", graph=_TRIGGER_GRAPH
    )
    workflow_b = await make_workflow(
        db_session, project_id=project_id, name="B", graph=_TRIGGER_GRAPH
    )
    await client.post(
        f"/api/v1/workflows/{workflow_a.id}/execute", headers=_auth(owner.token)
    )
    await client.post(
        f"/api/v1/workflows/{workflow_b.id}/execute", headers=_auth(owner.token)
    )

    response = await client.get(
        "/api/v1/executions",
        params={"projectId": project_id, "workflowId": str(workflow_a.id)},
        headers=_auth(owner.token),
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["workflowId"] == str(workflow_a.id)


async def test_cancel_a_queued_execution_marks_it_canceled_immediately(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    workflow = await make_workflow(
        db_session, project_id=project_id, graph=_TRIGGER_GRAPH
    )
    created = await client.post(
        f"/api/v1/workflows/{workflow.id}/execute", headers=_auth(owner.token)
    )
    execution_id = created.json()["executionId"]

    response = await client.post(
        f"/api/v1/executions/{execution_id}/cancel", headers=_auth(owner.token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "canceled"


async def test_retry_a_still_running_execution_is_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    workflow = await make_workflow(
        db_session, project_id=project_id, graph=_TRIGGER_GRAPH
    )
    created = await client.post(
        f"/api/v1/workflows/{workflow.id}/execute", headers=_auth(owner.token)
    )
    execution_id = created.json()["executionId"]

    response = await client.post(
        f"/api/v1/executions/{execution_id}/retry",
        json={"fromFailedNode": True},
        headers=_auth(owner.token),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "execution.not_retryable"


async def test_viewer_cannot_execute_but_can_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    workflow = await make_workflow(
        db_session, project_id=project_id, graph=_TRIGGER_GRAPH
    )
    viewer = await make_actor(
        db_session, email="viewer@example.com", org_name="Viewer Org", role=Role.VIEWER
    )
    from app.core.security import create_access_token
    from app.modules.organizations.models import OrganizationMember

    db_session.add(
        OrganizationMember(
            organization_id=owner.organization.id,
            user_id=viewer.user.id,
            role=Role.VIEWER,
        )
    )
    await db_session.flush()
    viewer_token = create_access_token(
        user_id=viewer.user.id,
        org_id=owner.organization.id,
        role=Role.VIEWER.value,
        jti="viewer-fixture",
    )

    execute = await client.post(
        f"/api/v1/workflows/{workflow.id}/execute", headers=_auth(viewer_token)
    )
    assert execute.status_code == 403, execute.text

    executions_list = await client.get(
        "/api/v1/executions",
        params={"projectId": project_id},
        headers=_auth(viewer_token),
    )
    assert executions_list.status_code == 200, executions_list.text
