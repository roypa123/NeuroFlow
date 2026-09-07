"""Organization-specific errors. Subclass the shared AppError hierarchy --
see docs/08-backend-architecture.md #8.5."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError
from app.core.exceptions import PermissionError as AppPermissionError


class OrganizationNotFoundError(NotFoundError):
    """Also raised for a real organization the caller isn't a member of --
    see docs/17-testing-strategy.md #17.4: a resource in a tenant you don't
    belong to must 404, never 403 (403 would confirm it exists)."""

    code = "organization.not_found"


class MemberNotFoundError(NotFoundError):
    code = "organization.member_not_found"


class LastOwnerError(AppPermissionError):
    code = "organization.last_owner"


class AlreadyMemberError(ConflictError):
    code = "organization.already_member"


class InvitationInvalidError(NotFoundError):
    code = "organization.invitation_invalid"


class InvitationEmailMismatchError(AppPermissionError):
    code = "organization.invitation_email_mismatch"
