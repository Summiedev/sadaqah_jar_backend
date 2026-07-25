"""Global exception handlers for Mizan.

Registers handlers that convert domain exceptions into the standard
error envelope:

{
  "error": {
    "code": "...",
    "message": "...",
    "details": {},
    "request_id": "...",
    "timestamp": "..."
  }
}
"""

import logging
import traceback
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

from app.core.exceptions import AppException
from app.core.observability import get_request_id

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict
    request_id: str | None = None
    timestamp: str | None = None


_EXCEPTION_STATUS_MAP = {
    "validation.error": status.HTTP_400_BAD_REQUEST,
    "auth.authentication_required": status.HTTP_401_UNAUTHORIZED,
    "auth.permission_denied": status.HTTP_403_FORBIDDEN,
    "resource.not_found": status.HTTP_404_NOT_FOUND,
    "resource.conflict": status.HTTP_409_CONFLICT,
    "business.rule_violated": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "rate.limit_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
    "external.service_error": status.HTTP_503_SERVICE_UNAVAILABLE,
    "infrastructure.error": status.HTTP_503_SERVICE_UNAVAILABLE,
    "internal.error": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "auth.username_taken": status.HTTP_409_CONFLICT,
    "auth.email_taken": status.HTTP_409_CONFLICT,
}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "http.error")
        message = detail.get("message", str(detail))
        details = detail.get("details", {})
    else:
        code = "http.error"
        message = str(detail)
        details = {}

    payload = ErrorResponse(
        code=code,
        message=message,
        details=details,
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(status_code=exc.status_code, content={"error": payload.model_dump()})


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    status_code = _EXCEPTION_STATUS_MAP.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    payload = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(status_code=status_code, content={"error": payload.model_dump()})


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id()
    logger.error(
        "Unhandled exception: %s\n%s",
        exc,
        traceback.format_exc(),
        extra={"request_id": request_id, "path": request.url.path},
    )
    payload = ErrorResponse(
        code="internal.error",
        message="Internal server error",
        details={},
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": payload.model_dump()}
    )
