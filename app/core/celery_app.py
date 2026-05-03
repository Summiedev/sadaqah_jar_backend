from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "sadaqah_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

celery_app.autodiscover_tasks(["app.tasks"])



celery_app.conf.beat_schedule = {
    "generate-daily-acts": {
        "task": "app.tasks.scheduled_tasks.generate_daily_acts",
        "schedule": crontab(hour=0, minute=1),
    },
    "check-streak": {
        "task": "app.tasks.scheduled_tasks.check_streak_integrity",
        "schedule": crontab(hour=2, minute=0),
    },
    "weekly-aggregate": {
        "task": "app.tasks.scheduled_tasks.aggregate_weekly_stats",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),
    },
    "jumua-reminder": {
    "task": "app.tasks.scheduled_tasks.friday_reminder",
    "schedule": crontab(hour=6, minute=0, day_of_week=5),
}
}