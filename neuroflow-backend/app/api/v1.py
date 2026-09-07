"""The only place routers are aggregated. See
docs/08-backend-architecture.md #8.2.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)

# Further module routers are included here as they land.
