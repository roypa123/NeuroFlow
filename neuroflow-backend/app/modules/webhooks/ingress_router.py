"""Webhook ingress routes -- deliberately NOT under `/api/v1` (mounted
directly on the app in `app.main`): third-party services register these
URLs permanently and they must survive an API version bump untouched. See
docs/11-api-design.md #11.12.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.modules.webhooks.ingress_controller import handle_webhook_request

router = APIRouter()

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@router.api_route("/webhook/{path:path}", methods=_METHODS)
async def production_webhook(path: str, request: Request) -> Response:
    return await handle_webhook_request(request, path, is_test=False)


@router.api_route("/webhook-test/{path:path}", methods=_METHODS)
async def test_webhook(path: str, request: Request) -> Response:
    return await handle_webhook_request(request, path, is_test=True)
