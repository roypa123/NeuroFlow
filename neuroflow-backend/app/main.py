"""FastAPI application factory: middleware, routers, lifespan, health.

The API server never imports app.engine or app.nodes -- see the
import-linter contract in docs/17-testing-strategy.md #17.7 and the
boundary rules in docs/03-system-architecture.md #3.9.
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    AccessLogMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from app.core.queue import close_arq_pool
from app.core.redis import get_redis
from app.modules.webhooks.ingress_router import router as webhook_ingress_router

logger = get_logger(__name__)

# A hard timeout per readiness check, run concurrently, is what actually
# makes /health/ready a *readiness* probe rather than a liveness probe with
# extra steps: an unreachable-but-not-actively-refusing dependency (a
# firewall drop, a half-open connection) can otherwise take the OS/driver's
# full connect timeout -- 10s+ per dependency, and additive if checked
# sequentially -- defeating orchestrators' short health-check windows
# (Kubernetes/Docker often default to 1-5s).
HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


def _verify_production_secrets(settings: Settings) -> None:
    """Refuse to boot in production without real secrets. A service that
    starts with a default signing key is a vulnerability nobody notices for
    months -- see docs/15-security-and-credentials.md #15.5."""
    if not settings.is_production:
        return
    missing = [
        name
        for name, value in (
            ("SECRET_KEY", settings.secret_key.get_secret_value()),
            (
                "CREDENTIAL_MASTER_KEY",
                settings.credential_master_key.get_secret_value(),
            ),
        )
        if not value
    ]
    if missing:
        print(
            f"FATAL: missing required secret(s) in production: {', '.join(missing)}",
            file=sys.stderr,
        )
        raise SystemExit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    _verify_production_secrets(settings)
    logger.info("app.startup", environment=settings.environment)
    yield
    await close_arq_pool()
    await engine.dispose()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NeuroFlow API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware order is behaviour -- see docs/08-backend-architecture.md #8.9.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        # AnyHttpUrl normalises "http://localhost:5173" to
        # "http://localhost:5173/" (trailing slash) -- but a browser's
        # Origin header never has one, and CORSMiddleware matches
        # allow_origins by exact string. Left un-stripped, no origin ever
        # matches and every cross-origin request is silently rejected.
        allow_origins=[str(o).rstrip("/") for o in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router)
    # Deliberately outside /api/v1 -- third-party services register these
    # URLs permanently and they must survive an API version bump untouched.
    # See docs/11-api-design.md #11.12.
    app.include_router(webhook_ingress_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness. No dependency checks -- see
        docs/16-observability.md #16.7."""
        return {"status": "ok"}

    async def _check_database() -> str:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"

    async def _check_redis() -> str:
        await get_redis().ping()
        return "ok"

    async def _timed(coro: Coroutine[Any, Any, str]) -> str:
        try:
            return await asyncio.wait_for(coro, timeout=HEALTH_CHECK_TIMEOUT_SECONDS)
        except Exception:  # noqa: BLE001 - readiness must never raise
            return "error"

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> JSONResponse:
        """Readiness: verifies Postgres and Redis are reachable."""
        database_status, redis_status = await asyncio.gather(
            _timed(_check_database()), _timed(_check_redis())
        )
        checks = {"database": database_status, "redis": redis_status}
        status_code = 200 if all(v == "ok" for v in checks.values()) else 503
        return JSONResponse(status_code=status_code, content=checks)

    return app


app = create_app()
