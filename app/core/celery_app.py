from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "sadaqah_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # Explicitly import every task module so both beat-dispatched
    # (scheduled_tasks) and event-driven (notification_tasks) tasks are
    # registered on every worker. Relying on autodiscover alone is fragile
    # because the default related_name ("tasks") does not match our module
    # names, which would leave deliver_event_notification unregistered.
    include=[
        "app.tasks.scheduled_tasks",
        "app.tasks.notification_tasks",
    ],
)


celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# Worker reliability: retry with exponential backoff, acknowledge on success
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.worker_prefetch_multiplier = 1

# Default task retry behaviour (individual tasks can override)
celery_app.conf.task_default_retry_delay = 60
celery_app.conf.task_default_max_retries = 3
celery_app.conf.task_time_limit = 300
celery_app.conf.task_soft_time_limit = 240

# ``include`` above guarantees both task modules are imported by every
# worker so beat-dispatched and event-driven tasks are registered. We keep
# autodiscover as a defensive fallback for any future task packages.
celery_app.autodiscover_tasks(["app.tasks"])

# Eagerly import the task modules at Celery-app construction time.
#
# ``include`` and ``autodiscover_tasks`` are BOTH lazy: they only import the
# listed modules when the worker finalizes (or on first ``send_task``). That
# means anything inspecting ``celery_app.tasks`` before a worker starts — most
# notably our tests and any synchronous ``.delay()`` from the web process on a
# cold import — sees an empty registry and the event-driven
# ``deliver_event_notification`` task appears unregistered. Importing the
# modules here registers their ``@celery_app.task`` decorators immediately,
# so the registry is correct the instant this module is imported.
#
# Imported at the bottom to avoid a circular import: the task modules import
# ``celery_app`` from this module.
from app.tasks import notification_tasks as _notification_tasks  # noqa: E402,F401
from app.tasks import scheduled_tasks as _scheduled_tasks  # noqa: E402,F401

        "task": "app.tasks.scheduled_tasks.aggregate_weekly_stats",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),
    },
}
