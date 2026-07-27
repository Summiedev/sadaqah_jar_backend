"""Global exception handlers for Mizan.

Registers handlers that convert domain exceptions into the standard
error envelope with user-friendly messages:

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
    "auth.invalid_credentials": status.HTTP_401_UNAUTHORIZED,
    "auth.invalid_token": status.HTTP_401_UNAUTHORIZED,
}

_FRIENDLY_MESSAGES = {
    "auth.authentication_required": "Please sign in to continue.",
    "auth.permission_denied": "You don't have permission to perform this action.",
    "resource.not_found": "The requested resource was not found.",
    "resource.conflict": "This resource already exists.",
    "business.rule_violated": "The action could not be completed. Please check your input and try again.",
    "rate.limit_exceeded": "Too many requests. Please wait a moment and try again.",
    "external.service_error": "An external service is temporarily unavailable. Please try again later.",
    "infrastructure.error": "A system error occurred. Please try again later.",
    "internal.error": "Something went wrong on our end. Please try again.",
    "auth.username_taken": "This username is already taken.",
    "auth.email_taken": "This email is already registered.",
    "auth.invalid_credentials": "Invalid email or password.",
    "auth.invalid_token": "This link is invalid or has expired.",
    "auth.email_already_verified": "Your email is already verified.",
    "auth.invalid_google_token": "Google authentication failed. Please try again.",
    "auth.google_email_unverified": "Your Google email is not verified.",
}


def _friendly_message(code: str, default_message: str) -> str:
    return _FRIENDLY_MESSAGES.get(code, default_message)


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

    friendly = _friendly_message(code, message)
    payload = ErrorResponse(
        code=code,
        message=friendly,
        details=details,
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(status_code=exc.status_code, content={"error": payload.model_dump()})


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    status_code = _EXCEPTION_STATUS_MAP.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    friendly = _friendly_message(exc.code, exc.message)
    payload = ErrorResponse(
        code=exc.code,
        message=friendly,
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
        message="Something went wrong on our end. Please try again.",
        details={},
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": payload.model_dump()}
    )