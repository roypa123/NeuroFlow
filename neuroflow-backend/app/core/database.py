"""Async SQLAlchemy engine, session factory, and the request-scoped session
dependency.

Transaction boundary is the request: get_session commits on success and
rolls back on any exception. Services never call commit() themselves -- see
docs/08-backend-architecture.md #8.4.
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

if sys.platform == "win32":
    # psycopg's async mode cannot run under Windows' default
    # ProactorEventLoop -- it requires a selector-based loop (this bites
    # every entrypoint that imports this module: uvicorn, arq, the
    # scheduler, and `alembic` -- alembic/env.py carries its own copy of
    # this fix since it runs before app.core.database is ever imported).
    # Deployed targets (Docker/Linux) already default to a selector loop,
    # so this only matters for local Windows development.
    #
    # WindowsSelectorEventLoopPolicy is deprecated (slated for removal in
    # 3.16) in favour of asyncio.run(loop_factory=...), which uvicorn's
    # public API does not expose a way to pass through -- revisit if/when
    # it does.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
        echo=settings.debug,
    )


engine: AsyncEngine = _build_engine()

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, committed or rolled back
    when the request completes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Equivalent to get_session(), for callers with no Depends() machinery
    (the worker, the scheduler, scripts)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
