"""RBAC matrix -- transcribed from docs/15-security-and-credentials.md #15.4.
A wrong entry here is a real security regression, so the matrix is asserted
row by row rather than spot-checked."""
from __future__ import annotations

import pytest

from app.core.exceptions import PermissionError as AppPermissionError
from app.core.permissions import Permission, Role, require, role_has_permission


def test_owner_has_every_permission() -> None:
    for permission in Permission:
        assert role_has_permission(Role.OWNER, permission)


def test_admin_has_every_permission_except_billing() -> None:
    for permission in Permission:
        expected = permission is not Permission.ORG_BILLING
        assert role_has_permission(Role.ADMIN, permission) is expected


def test_member_can_build_and_run_but_not_manage_members() -> None:
    assert role_has_permission(Role.MEMBER, Permission.WORKFLOW_WRITE)
    assert role_has_permission(Role.MEMBER, Permission.WORKFLOW_EXECUTE)
    assert role_has_permission(Role.MEMBER, Permission.CREDENTIAL_USE)
    assert not role_has_permission(Role.MEMBER, Permission.MEMBER_MANAGE)
    assert not role_has_permission(Role.MEMBER, Permission.AUDIT_READ)
    assert not role_has_permission(Role.MEMBER, Permission.ORG_BILLING)


def test_viewer_can_only_read() -> None:
    assert role_has_permission(Role.VIEWER, Permission.WORKFLOW_READ)
    assert role_has_permission(Role.VIEWER, Permission.EXECUTION_READ)
    assert not role_has_permission(Role.VIEWER, Permission.WORKFLOW_WRITE)
    assert not role_has_permission(Role.VIEWER, Permission.WORKFLOW_EXECUTE)
    assert not role_has_permission(Role.VIEWER, Permission.CREDENTIAL_WRITE)


def test_require_raises_for_missing_permission() -> None:
    with pytest.raises(AppPermissionError):
        require(Role.VIEWER, Permission.WORKFLOW_WRITE)


def test_require_raises_for_no_role() -> None:
    with pytest.raises(AppPermissionError):
        require(None, Permission.WORKFLOW_READ)


def test_require_passes_silently_when_permitted() -> None:
    require(Role.OWNER, Permission.ORG_BILLING)  # must not raise
