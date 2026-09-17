"""Small, dependency-free Celery/Redis operational telemetry.

This is deliberately lightweight for the production VPS. Queue depth is read
from Redis, while task failures are counted and logged at ERROR level so the
container log/alerting pipeline can surface them without a second monitoring
service.
"""

import logging
from datetime import datetime, timezone

import redis
from celery.signals import task_failure, task_retry

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

QUEUE_NAMES = ("default", "notifications", "reminders", "analytics", "celery")
_FAILURE_KEY = "mizan:celery:task_failures"
_FAILURE_TTL = 7 * 24 * 60 * 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def queue_snapshot() -> dict:
    """Return queue depths and the last recorded task failures."""
    try:
        pipeline = redis_client.pipeline()
        for queue in QUEUE_NAMES:
            pipeline.llen(queue)
        depths = dict(zip(QUEUE_NAMES, pipeline.execute(), strict=True))
        failures = redis_client.hgetall(_FAILURE_KEY)
        decoded_failures = {
            (key.decode() if isinstance(key, bytes) else str(key)): int(value)
            for key, value in failures.items()
        }
        return {
            "status": "ok",
            "checked_at": _now(),
            "queues": depths,
            "total_depth": sum(depths.values()),
            "task_failures_7d": decoded_failures,
        }
    except (redis.RedisError, ValueError) as exc:
        logger.warning("Celery queue telemetry unavailable: %s", exc)
        return {"status": "unavailable", "checked_at": _now()}


def _record_failure(task_name: str | None) -> None:
    name = task_name or "unknown"
    try:
        redis_client.hincrby(_FAILURE_KEY, name, 1)
        redis_client.expire(_FAILURE_KEY, _FAILURE_TTL)
    except redis.RedisError as exc:
        logger.warning("Could not record Celery task failure: %s", exc)


@task_failure.connect(weak=False)
def on_task_failure(
    task_id=None, task=None, exception=None, einfo=None, sender=None, **kwargs
):
    """Emit an actionable failure alert without logging task arguments."""
    task_name = getattr(task, "name", None) or getattr(sender, "name", None)
    _record_failure(task_name)
    logger.error(
        "Celery task failed task=%s task_id=%s exception_type=%s exception=%s",
        task_name or "unknown",
        task_id or "unknown",
        type(exception).__name__ if exception else "unknown",
        str(exception)[:500] if exception else "unknown",
    )


@task_retry.connect(weak=False)
def on_task_retry(request=None, reason=None, **kwargs):
    task_name = getattr(request, "task", None) or "unknown"
    logger.warning(
        "Celery task retrying task=%s task_id=%s reason=%s",
        task_name,
        getattr(request, "id", "unknown"),
        str(reason)[:500] if reason else "unknown",
    )
