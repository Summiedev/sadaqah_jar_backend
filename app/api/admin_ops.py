"""Protected operational views for worker and queue diagnostics."""

from fastapi import APIRouter, Depends

from app.core.celery_monitor import queue_snapshot
from app.core.dependencies import require_admin
from app.core.observability import request_metrics

router = APIRouter(prefix="/admin/ops", tags=["Admin Operations"])


@router.get("/celery")
def celery_status(admin=Depends(require_admin)):
    """Return queue depth/failure counters without exposing task payloads."""
    return {
        "celery": queue_snapshot(),
        "http": request_metrics.snapshot(),
    }
