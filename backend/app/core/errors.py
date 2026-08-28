"""Typed errors + FastAPI handlers. One envelope:
{"error": {"type": "...", "message": "...", "request_id": "..."}}"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger, get_request_id

log = get_logger(__name__)


class AppError(Exception):
    status_code = 400
    error_type = "app_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BadInputError(AppError):
    status_code = 400
    error_type = "bad_input"


class NotFoundError(AppError):
    status_code = 404
    error_type = "not_found"


class ConflictError(AppError):
    status_code = 409
    error_type = "conflict"


def _envelope(error_type: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"type": error_type, "message": message, "request_id": get_request_id()}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        log.warning("app_error type=%s msg=%s", exc.error_type, exc.message)
        return _envelope(exc.error_type, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _envelope("validation_error", "Request payload failed validation.", 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return _envelope("http_error", str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.exception("unhandled_exception: %s", exc)
        return _envelope("internal_error", "An unexpected error occurred.", 500)
