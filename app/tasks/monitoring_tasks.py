"""Periodic operational checks for the Celery/Redis worker runtime."""

import logging

from app.core.celery_app import celery_app
from app.core.celery_monitor import queue_snapshot

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.monitoring_tasks.monitor_celery_queues")
def monitor_celery_queues() -> dict:
    snapshot = queue_snapshot()
    if snapshot.get("status") != "ok":
        logger.error("Celery queue monitor could not read Redis")
        return snapshot

    total_depth = snapshot.get("total_depth", 0)
    # This is an alert signal, not a task-killing threshold. The worker keeps
    # processing while operators investigate a growing backlog.
    if total_depth >= 100:
        logger.error(
            "Celery queue backlog is high total_depth=%s queues=%s",
            total_depth,
            snapshot.get("queues", {}),
        )
    else:
        logger.info("Celery queue snapshot: %s", snapshot)
    return snapshot
