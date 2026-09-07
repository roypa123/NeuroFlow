"""Workflow CRUD, versioning, optimistic concurrency, duplication, and
export/import. See docs/09-domain-modules.md #9.8 and
docs/11-api-design.md #11.7."""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.core.security import create_access_token
from app.modules.organizations.models import OrganizationMember
from tests.factories import Actor, make_actor, make_project


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_project_owner(db_session: AsyncSession) -> tuple[Actor, str]:
    owner = await make_actor(
        db_session, email="owner@example.com", org_name="Org", role=Role.OWNER
    )
    project = await make_project(db_session, organization_id=owner.organization.id)
    return owner, str(project.id)


async def test_create_workflow_starts_at_version_one_with_an_empty_graph(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)

    response = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "My Workflow"},
        headers=_auth(owner.token),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "My Workflow"
    assert body["version"] == 1
    empty_graph = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    assert body["graph"] == empty_graph
    assert body["isActive"] is False


async def test_saving_the_same_graph_twice_does_not_create_a_new_version(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "WF"},
        headers=_auth(owner.token),
    )
    workflow = create.json()
    graph = {
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

    first = await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": workflow["activeVersionId"]},
        headers=_auth(owner.token),
    )
    assert first.status_code == 200, first.text
    assert first.json()["version"] == 2

    # Re-saving the identical graph must dedupe rather than growing the
    # version history -- see docs/10-database-schema.md #10.4's checksum.
    second = await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": first.json()["activeVersionId"]},
        headers=_auth(owner.token),
    )
    assert second.status_code == 200, second.text
    assert second.json()["version"] == 2


async def test_stale_base_version_id_is_a_409_with_the_actual_version_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "WF"},
        headers=_auth(owner.token),
    )
    workflow = create.json()
    graph = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}

    response = await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": "00000000-0000-0000-0000-000000000000"},
        headers=_auth(owner.token),
    )

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "workflow.version_conflict"
    assert error["details"]["actualVersionId"] == workflow["activeVersionId"]


async def test_unknown_node_type_fails_validation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "WF"},
        headers=_auth(owner.token),
    )
    workflow = create.json()
    graph = {
        "nodes": [
            {
                "id": "n1",
                "type": "neuroflow.doesNotExist",
                "position": {"x": 0, "y": 0},
                "parameters": {},
            }
        ],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }

    response = await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": workflow["activeVersionId"]},
        headers=_auth(owner.token),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "workflow.invalid_graph"


async def test_viewer_cannot_write_but_can_read(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "WF"},
        headers=_auth(owner.token),
    )
    workflow_id = create.json()["id"]

    viewer = await make_actor(
        db_session, email="viewer@example.com", org_name="Viewer Org", role=Role.VIEWER
    )
    # make_actor always creates a fresh org; add the viewer to the owner's
    # org instead so they're actually a member of the workflow's tenant.
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

    read = await client.get(
        f"/api/v1/workflows/{workflow_id}", headers=_auth(viewer_token)
    )
    assert read.status_code == 200, read.text

    write = await client.patch(
        f"/api/v1/workflows/{workflow_id}",
        json={"name": "Hijacked"},
        headers=_auth(viewer_token),
    )
    assert write.status_code == 403, write.text


async def test_duplicate_copies_the_active_graph_into_a_new_workflow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "Original"},
        headers=_auth(owner.token),
    )
    workflow = create.json()
    graph = {
        "nodes": [
            {
                "id": "n1",
                "type": "neuroflow.noOp",
                "position": {"x": 0, "y": 0},
                "parameters": {},
            }
        ],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
    await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": workflow["activeVersionId"]},
        headers=_auth(owner.token),
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow['id']}/duplicate",
        json={},
        headers=_auth(owner.token),
    )

    assert response.status_code == 201, response.text
    copy = response.json()
    assert copy["id"] != workflow["id"]
    assert copy["name"] == "Original (copy)"
    assert copy["graph"]["nodes"][0]["type"] == "neuroflow.noOp"


async def test_export_then_import_round_trips_the_graph(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "Exportable"},
        headers=_auth(owner.token),
    )
    workflow = create.json()
    graph = {
        "nodes": [
            {
                "id": "n1",
                "type": "neuroflow.set",
                "typeVersion": 1,
                "name": None,
                "position": {"x": 10, "y": 20},
                "parameters": {"mode": "merge", "fields": {"ok": True}},
            }
        ],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
    await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": workflow["activeVersionId"]},
        headers=_auth(owner.token),
    )

    exported = await client.get(
        f"/api/v1/workflows/{workflow['id']}/export", headers=_auth(owner.token)
    )
    assert exported.status_code == 200, exported.text
    export_doc = exported.json()

    imported = await client.post(
        "/api/v1/workflows/import",
        json={
            "projectId": project_id,
            "name": export_doc["name"] + " (imported)",
            "settings": export_doc["settings"],
            "graph": export_doc["graph"],
        },
        headers=_auth(owner.token),
    )

    assert imported.status_code == 201, imported.text
    assert imported.json()["graph"] == graph


async def test_activate_requires_exactly_one_trigger_node(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, project_id = await _make_project_owner(db_session)
    create = await client.post(
        "/api/v1/workflows",
        json={"projectId": project_id, "name": "No Trigger"},
        headers=_auth(owner.token),
    )
    workflow = create.json()

    response = await client.post(
        f"/api/v1/workflows/{workflow['id']}/activate", headers=_auth(owner.token)
    )

    assert response.status_code == 422, response.text

    graph = {
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
    await client.patch(
        f"/api/v1/workflows/{workflow['id']}",
        json={"graph": graph, "baseVersionId": workflow["activeVersionId"]},
        headers=_auth(owner.token),
    )

    activated = await client.post(
        f"/api/v1/workflows/{workflow['id']}/activate", headers=_auth(owner.token)
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["isActive"] is True
