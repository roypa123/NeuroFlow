"""The AppError hierarchy and the single place it is translated to HTTP.

Services raise these, never HTTPException -- that is what keeps a service
callable from the worker, which has no HTTP context at all. See
docs/08-backend-architecture.md #8.5 and docs/11-api-design.md #11.4.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base of every domain error. Subclass per failure, not per module."""

    code: str = "internal_error"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND


class ValidationError(AppError):
    code = "validation_error"
    http_status = status.HTTP_422_UNPROCESSABLE_CONTENT


class PermissionError(AppError):  # noqa: A001 - deliberate: matches docs
    code = "forbidden"
    http_status = status.HTTP_403_FORBIDDEN


class ConflictError(AppError):
    code = "conflict"
    http_status = status.HTTP_409_CONFLICT


class RateLimitError(AppError):
    code = "rate_limited"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class ExternalServiceError(AppError):
    code = "external_service_error"
    http_status = status.HTTP_502_BAD_GATEWAY


def _error_body(code: str, message: str, request: Request, details: Any = None) -> dict:
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {"code": code, "message": message, "requestId": request_id}
    if details is not None:
        body["details"] = details
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.http_status >= 500:
            logger.error("unhandled_app_error", code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.code, exc.message, request, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail), request),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unexpected_error", error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "internal_error", "An unexpected error occurred.", request
            ),
        )
