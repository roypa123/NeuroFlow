"""The only place routers are aggregated. See
docs/08-backend-architecture.md #8.2.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import api_keys_router
from app.modules.auth.router import router as auth_router
from app.modules.credentials.router import credential_types_router
from app.modules.credentials.router import router as credentials_router
from app.modules.executions.router import router as executions_router
from app.modules.nodes.router import router as node_types_router
from app.modules.organizations.router import invitations_router
from app.modules.organizations.router import router as organizations_router
from app.modules.projects.router import router as projects_router
from app.modules.variables.router import router as variables_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.workflows.router import router as workflows_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(api_keys_router)
router.include_router(organizations_router)
router.include_router(invitations_router)
router.include_router(projects_router)
router.include_router(audit_router)
router.include_router(node_types_router)
router.include_router(workflows_router)
router.include_router(executions_router)
router.include_router(credentials_router)
router.include_router(credential_types_router)
router.include_router(webhooks_router)
router.include_router(variables_router)

# Further module routers are included here as they land.
