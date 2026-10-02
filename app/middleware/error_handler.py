from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.schemas.common import ErrorDetail, ErrorResponse
from app.utils.validation_errors import format_validation_errors

logger = logging.getLogger("app.errors")


def _error_payload(
    *,
    code: str,
    message: str,
    details: Optional[object] = None,
    request: Optional[Request] = None,
) -> dict:
    request_id = getattr(request.state, "request_id", None) if request else None
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=request_id,
    ).model_dump()
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error code=%s status=%s request_id=%s path=%s message=%s",
            exc.code,
            exc.status_code,
            getattr(request.state, "request_id", None),
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code=exc.code, message=exc.message, details=exc.details, request=request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        raw_errors = jsonable_encoder(exc.errors())
        formatted = format_validation_errors(raw_errors if isinstance(raw_errors, list) else [])
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                code="validation_error",
                message="Request validation failed",
                details={"errors": formatted},
                request=request,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code="http_error", message=str(exc.detail), request=request),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        settings = get_settings()
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled_error request_id=%s path=%s", request_id, request.url.path)
        message = str(exc) if settings.debug else "Internal server error"
        return JSONResponse(
            status_code=500,
            content=_error_payload(code="internal_error", message=message, request=request),
        )
