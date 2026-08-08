from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.exception_handlers import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
)
from app.core.observability import set_request_id
from app.core.logger import logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate push delivery configuration at startup so operators
    # immediately see whether FCM is live. This never raises: a misconfigured
    # FCM setup degrades to a no-op rather than blocking API startup.
    try:
        from app.services.push_notification_service import validate_push_configuration

        validate_push_configuration()
    except Exception:
        logger.exception("Push configuration validation raised unexpectedly")

    # Capture the running event loop so synchronous (threadpool) route handlers
    # can schedule websocket sends via manager.send_user_event_threadsafe().
    try:
        from app.core.ws_manager import manager

        manager.bind_loop()
        manager.start_pubsub_listener()
    except Exception:
        logger.exception("Failed to bind websocket event loop at startup")

    logger.info("API startup complete")

    yield
    try:
        from app.core.ws_manager import manager

        manager.stop_pubsub_listener()
    except Exception:
        logger.exception("Failed to stop websocket Redis listener")
    logger.info("API shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    exception_handlers={
        HTTPException: http_exception_handler,
        AppException: app_exception_handler,
        Exception: general_exception_handler,
    },
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
