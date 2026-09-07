"""Async SQLAlchemy engine, session factory, and the request-scoped session
dependency.

Transaction boundary is the request: get_session commits on success and
rolls back on any exception. Services never call commit() themselves -- see
docs/08-backend-architecture.md #8.4.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


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
