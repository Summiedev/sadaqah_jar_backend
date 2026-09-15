import uuid
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.journey.models import JourneyPrayerCompletion
from app.main import app
from app.models.user import User
from app.users.models import UserPreference


client = TestClient(app)


def test_prayer_checkoff_sync_is_idempotent_and_reversible():
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:10]
    user = User(
        username=f"prayer_sync_{suffix}",
        email=f"prayer_sync_{suffix}@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    local_date = date(2026, 9, 15).isoformat()

    try:
        payload = {
            "local_date": local_date,
            "prayer_name": "fajr",
            "completed": True,
        }
        first = client.put(
            "/api/v1/journey/prayers/progress", json=payload, headers=headers
        )
        second = client.put(
            "/api/v1/journey/prayers/progress", json=payload, headers=headers
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["completed_prayers"] == ["fajr"]

        read = client.get(
            "/api/v1/journey/prayers/progress",
            params={"local_date": local_date},
            headers=headers,
        )
        assert read.status_code == 200
        assert read.json()["data"]["completed_prayers"] == ["fajr"]

        undone = client.put(
            "/api/v1/journey/prayers/progress",
            json={**payload, "completed": False},
            headers=headers,
        )
        assert undone.status_code == 200
        assert undone.json()["data"]["completed_prayers"] == []
    finally:
        db.query(JourneyPrayerCompletion).filter(
            JourneyPrayerCompletion.user_id == user.id
        ).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_worship_reminder_preferences_round_trip():
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:10]
    user = User(
        username=f"reminder_prefs_{suffix}",
        email=f"reminder_prefs_{suffix}@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"
    }
    reminder_preferences = {
        "prayer_reminders": {"fajr": {"enabled": False, "offset_minutes": -5}},
        "daily_times": {"morning_adhkar": "07:30", "quran": "19:00"},
        "friday_reminder": True,
        "tahajjud": False,
    }

    try:
        with patch("app.notifications.router.schedule_user_aware_reminders.apply_async"):
            saved = client.put(
                "/api/v1/notifications/preferences",
                json={"reminder_preferences": reminder_preferences},
                headers=headers,
            )
            fetched = client.get(
                "/api/v1/notifications/preferences", headers=headers
            )

        assert saved.status_code == 200
        assert saved.json()["data"]["reminder_preferences"] == reminder_preferences
        assert fetched.status_code == 200
        assert fetched.json()["data"]["reminder_preferences"] == reminder_preferences
        assert db.get(UserPreference, user.id).reminder_preferences
    finally:
        db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
        db.close()
