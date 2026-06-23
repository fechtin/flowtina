"""Domain exceptions and a global exception handler.

All custom exceptions carry an HTTP status code and a machine-readable ``code``
so the API layer can return a consistent error envelope.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """Base application exception."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "", *, details: Any | None = None) -> None:
        self.message = message or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    status_code = 400
    code = "VALIDATION_ERROR"


class AuthenticationException(AppException):
    status_code = 401
    code = "UNAUTHORIZED"


class PermissionException(AppException):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundException(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ConflictException(AppException):
    status_code = 409
    code = "CONFLICT"


class RateLimitException(AppException):
    status_code = 429
    code = "TOO_MANY_REQUESTS"


class BusinessException(AppException):
    status_code = 422
    code = "BUSINESS_ERROR"


class ProviderException(AppException):
    status_code = 502
    code = "PROVIDER_ERROR"


class SchedulerException(AppException):
    status_code = 500
    code = "SCHEDULER_ERROR"


class FacebookException(AppException):
    status_code = 502
    code = "FACEBOOK_ERROR"


class TelegramException(AppException):
    status_code = 502
    code = "TELEGRAM_ERROR"


def _error_body(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"success": False, "error": err}


def register_exception_handlers(app: Any) -> None:
    """Attach global exception handlers to the FastAPI app."""
    from loguru import logger

    @app.exception_handler(AppException)
    async def _app_exc(_: Request, exc: AppException) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error(f"{exc.code}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_error_body("VALIDATION_ERROR", "Invalid request", exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 429: "TOO_MANY_REQUESTS"}
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code_map.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "Internal server error"),
        )
