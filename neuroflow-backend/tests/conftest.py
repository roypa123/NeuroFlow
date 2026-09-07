"""Shared pytest fixtures.

Phase 1's tests were unit-level plus one integration test against
/health that, by design, needs no real dependency. Phase 2 is the first
module with real domain data, so the testcontainers-backed Postgres
fixtures described in docs/17-testing-strategy.md #17.4 land here:
`postgres_dsn` starts one real container for the whole session, migrated
via `alembic upgrade head` (never `metadata.create_all()` -- this is what
actually exercises the migrations), and `db_session` gives each test its
own transaction, rolled back afterwards, joined via SQLAlchemy's
"external transaction" pattern so the app's own `session.commit()` calls
during a request only release a savepoint rather than escaping the test's
rollback.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

# Settings are validated at import time (docs/08-backend-architecture.md
# #8.8), so tests need a minimally valid environment before anything in
# app.core.config is imported. Set these before any app import happens.
# DATABASE_URL/REDIS_URL here point at nothing reachable on purpose --
# test_health.py relies on exactly that; anything needing a real database
# gets it from the postgres_dsn/db_session fixtures below instead, via a
# FastAPI dependency override rather than by changing these.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "CREDENTIAL_MASTER_KEY", "dGVzdC1tYXN0ZXIta2V5LTMyLWJ5dGVzLWV4YWN0bHkh"
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _to_async_dsn(sync_dsn: str) -> str:
    """testcontainers hands back a psycopg2-style URL; the app is built on
    psycopg3's async mode."""
    _, _, rest = sync_dsn.partition("://")
    return f"postgresql+psycopg://{rest}"


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterator[str]:
    with PostgresContainer("postgres:18-alpine") as container:
        yield _to_async_dsn(container.get_connection_url())


@pytest.fixture(scope="session")
async def migrated_engine(postgres_dsn: str) -> AsyncIterator[AsyncEngine]:
    # sys.executable, not a bare "alembic", so this resolves the same
    # interpreter/venv running pytest itself regardless of PATH.
    subprocess.run(  # noqa: S603 -- fixed argv, no untrusted input
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": postgres_dsn},
        check=True,
    )
    engine = create_async_engine(postgres_dsn)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(migrated_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with migrated_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """The real ASGI app, wired to this test's transactional session via a
    dependency override -- not a second app instance, so routing/middleware
    behave exactly as in production."""
    from app.core.database import get_session
    from app.main import app

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)
