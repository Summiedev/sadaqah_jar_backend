from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.user import User
from app.services.personalization_service import generate_personalized_acts
from app.services.notification_service import send_push_notification
from app.services.streak_service import validate_streak
    
from app.services.analytics_service import compute_weekly_stats


@celery_app.task
def generate_daily_acts():
    db = SessionLocal()
    users = db.query(User).filter(User.is_active == True).all()

    for user in users:
        generate_personalized_acts(db, user)

    db.close()

@celery_app.task
def check_streak_integrity():
    db = SessionLocal()
    users = db.query(User).all()

    for user in users:
        validate_streak(db, user.id)

    db.close()
    
@celery_app.task
def send_morning_reminder():
    db = SessionLocal()
    users = db.query(User).all()

    for user in users:
        if not user.has_completed_today:
            send_push_notification(
                user.device_token,
                "🌅 Start your day with a good deed."
            )

    db.close()

@celery_app.task
def aggregate_weekly_stats():
    db = SessionLocal()
    compute_weekly_stats(db)
    db.close()

@celery_app.task
def jar_completion_celebration(user_id: int):
    db = SessionLocal()

    # Send notification
    send_push_notification(
        user_id,
        "🎉 Your Sadaqah Jar is Complete!"
    )

    # Analytics hook
    # increment completion metrics

    db.close()
    
@celery_app.task
@celery_app.task
def send_friday_reminder():
    db = SessionLocal()

    users = db.query(User).filter(User.friday_reminder == True).all()

    for user in users:
        send_push_notification(
            user.id,
            "🌙 It's Jumu’ah! Earn extra stars today."
        )

    db.close()