"""FastAPI application factory: middleware, routers, lifespan, health.

The API server never imports app.engine or app.nodes -- see the
import-linter contract in docs/17-testing-strategy.md #17.7 and the
boundary rules in docs/03-system-architecture.md #3.9.
"""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
from app.core.redis import get_redis

logger = get_logger(__name__)


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
        allow_origins=[str(o) for o in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)
    app.include_router(api_v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness. No dependency checks -- see
        docs/16-observability.md #16.7."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> JSONResponse:
        """Readiness: verifies Postgres and Redis are reachable."""
        checks = {"database": "unknown", "redis": "unknown"}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:  # noqa: BLE001 - readiness must never raise
            checks["database"] = "error"
        try:
            await get_redis().ping()
            checks["redis"] = "ok"
        except Exception:  # noqa: BLE001
            checks["redis"] = "error"

        status_code = 200 if all(v == "ok" for v in checks.values()) else 503
        return JSONResponse(status_code=status_code, content=checks)

    return app


app = create_app()
