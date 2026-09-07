"""The only place routers are aggregated. See
docs/08-backend-architecture.md #8.2.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import api_keys_router
from app.modules.auth.router import router as auth_router
from app.modules.organizations.router import invitations_router
from app.modules.organizations.router import router as organizations_router
from app.modules.projects.router import router as projects_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(api_keys_router)
router.include_router(organizations_router)
router.include_router(invitations_router)
router.include_router(projects_router)
router.include_router(audit_router)

# Further module routers are included here as they land.
