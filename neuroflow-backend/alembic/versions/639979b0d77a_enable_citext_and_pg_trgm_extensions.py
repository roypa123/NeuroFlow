"""enable citext and pg_trgm extensions

Revision ID: 639979b0d77a
Revises:
Create Date: 2026-09-07 11:57:57.597003

Enables the two Postgres extensions the schema design depends on:
- citext: case-insensitive uniqueness for email/slug at the database level
  (see docs/10-database-schema.md #10.3).
- pg_trgm: trigram search, used for workflow name search
  (see docs/10-database-schema.md #10.12).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "639979b0d77a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS citext")
