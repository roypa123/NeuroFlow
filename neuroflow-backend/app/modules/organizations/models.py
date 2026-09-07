"""Organization and membership models. See docs/09-domain-modules.md #9.4
and docs/10-database-schema.md #10.4."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import Role
from app.core.types import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.modules.users.models import User

_ROLE_TYPE = SAEnum(
    Role, name="org_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]
)


class Organization(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))

    members: Mapped[list[OrganizationMember]] = relationship(
        back_populates="organization"
    )


class OrganizationMember(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(_ROLE_TYPE)

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Invitation(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "invitations"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[Role] = mapped_column(_ROLE_TYPE)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
