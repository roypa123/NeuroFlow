"""RBAC matrix and the require() helper. Called only from controllers --
never from services, which the worker also uses with no user in scope. See
docs/15-security-and-credentials.md #15.4.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from app.core.exceptions import PermissionError as AppPermissionError

if TYPE_CHECKING:
    from uuid import UUID


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(str, Enum):
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_ACTIVATE = "workflow:activate"
    WORKFLOW_EXECUTE = "workflow:execute"
    EXECUTION_READ = "execution:read"
    EXECUTION_DATA_READ = "execution:data:read"
    CREDENTIAL_WRITE = "credential:write"
    CREDENTIAL_USE = "credential:use"
    MEMBER_MANAGE = "member:manage"
    API_KEY_MANAGE = "api_key:manage"
    AUDIT_READ = "audit:read"
    ORG_BILLING = "org:billing"


# Role -> permissions it holds. Table transcribed from
# docs/15-security-and-credentials.md #15.4.
_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(Permission) - {Permission.ORG_BILLING},
    Role.MEMBER: frozenset(
        {
            Permission.WORKFLOW_READ,
            Permission.WORKFLOW_WRITE,
            Permission.WORKFLOW_DELETE,
            Permission.WORKFLOW_ACTIVATE,
            Permission.WORKFLOW_EXECUTE,
            Permission.EXECUTION_READ,
            Permission.EXECUTION_DATA_READ,
            Permission.CREDENTIAL_WRITE,
            Permission.CREDENTIAL_USE,
        }
    ),
    Role.VIEWER: frozenset({Permission.WORKFLOW_READ, Permission.EXECUTION_READ}),
}


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS.get(role, frozenset())


def require(
    role: Role | None,
    permission: Permission,
    *,
    resource_id: UUID | None = None,  # noqa: ARG001 -- reserved, see docstring
) -> None:
    """Raise PermissionError unless role grants permission.

    resource_id is accepted (and currently unused beyond documentation
    intent) so call sites read naturally; a future revision may use it for
    per-resource share overrides.
    """
    if role is None or not role_has_permission(role, permission):
        raise AppPermissionError(f"Missing permission: {permission.value}")
