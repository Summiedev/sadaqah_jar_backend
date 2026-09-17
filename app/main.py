from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
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
from app.core.observability import request_metrics, set_request_id, start_timer
from app.core.logger import logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = start_timer()
        try:
            response = await call_next(request)
        except Exception:
            request_metrics.record_request(
                request.method,
                request.url.path,
                500,
                start_timer() - started,
            )
            raise
        request_metrics.record_request(
            request.method,
            request.url.path,
            response.status_code,
            start_timer() - started,
        )
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

        push_status = validate_push_configuration()
        if (
            settings.ENV.lower() in {"production", "prod"}
            and not push_status["enabled"]
        ):
            raise RuntimeError(
                "Push delivery is not configured for production. Set "
                "FCM_SERVICE_ACCOUNT_PATH to a valid Firebase service account."
            )
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
app.add_middleware(RequestMetricsMiddleware)
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


@app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics():
    """Expose aggregate process metrics for an internal scraper."""
    return request_metrics.prometheus()


@app.get("/readiness")
def readiness():
    """Report dependency readiness for deploy/load-balancer probes.

    ``/health`` remains a cheap liveness probe. This endpoint verifies the
    dependencies that are required to serve authenticated application traffic
    and makes notification configuration visible to operators without leaking
    credential paths or secrets.
    """
    from fastapi.responses import JSONResponse
    from sqlalchemy import text

    checks: dict[str, object] = {}
    try:
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Readiness database check failed")
        checks["database"] = "unavailable"

    try:
        from app.core.cache import redis_client

        redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Readiness Redis check failed")
        checks["redis"] = "unavailable"

    if settings.CELERY_READINESS_REQUIRED:
        try:
            from app.core.celery_app import celery_app

            workers = celery_app.control.inspect(
                timeout=settings.CELERY_INSPECT_TIMEOUT_SECONDS
            ).ping()
            checks["celery"] = "ok" if workers else "no_worker"
        except Exception:
            logger.exception("Readiness Celery worker check failed")
            checks["celery"] = "unavailable"
    else:
        checks["celery"] = "not_checked"

    try:
        from app.services.push_notification_service import validate_push_configuration

        push = validate_push_configuration()
        checks["push"] = "ok" if push["enabled"] else push["reason"]
    except Exception:
        logger.exception("Readiness push check failed")
        checks["push"] = "unavailable"

    ready = checks["database"] == "ok" and checks["redis"] == "ok"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
