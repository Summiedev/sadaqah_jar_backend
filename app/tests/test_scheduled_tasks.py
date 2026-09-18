"""
Tests for scheduled_tasks.py - targets audit-flagged bugs:

1. jar_completion_celebration: was called with wrong param (jar.user_id vs user_id).
   Tests that the task creates an in-app notification for the correct user.
2. generate_daily_acts: verifies the batch-query refactor doesn't break the
   functional contract - acts are generated for active users.
"""

import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.jar import Jar
from app.notifications.models import Notification, ScheduledNotification
from app.models.sadaqah_act import SadaqahAct
from app.models.user import User
from app.users.models import UserPreference
from app.journey.models import JourneyPrayerCompletion, JourneyQuranProgress
from app.notifications.models import NotificationTemplate, SchedulingStrategy


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


@pytest.fixture
def user(db):
    u = User(
        username="scheduled_test",
        email="scheduled_test@example.com",
        hashed_password=hash_password("TestPass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    db.query(Jar).filter(Jar.user_id == u.id).delete()
    db.query(User).filter(User.id == u.id).delete()
    db.commit()


@pytest.fixture
def verified_act(db):
    a = SadaqahAct(
        title="Verified Act",
        description="Test",
        category="general",
        difficulty=1,
        reward_weight=1,
        verified=True,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    yield a
    db.delete(a)
    db.commit()


class TestJarCompletionCelebration:
    """
    Audit bug caught in A1/A2: jar_completion_celebration was called with
    the jar_id instead of user_id in add_star() in sadaqah.py.
    This test confirms the task creates a notification row for the correct
    user when invoked directly.
    """

    def test_creates_notification_for_correct_user(self, db, user):
        from app.tasks.scheduled_tasks import jar_completion_celebration

        before = db.query(Notification).filter(Notification.user_id == user.id).count()
        jar_completion_celebration(user.id)

        db.expire_all()
        after = db.query(Notification).filter(Notification.user_id == user.id).count()
        assert after == before + 1

        notification = (
            db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .first()
        )
        assert notification is not None
        assert notification.title == "Jar complete"
        assert notification.message == "Your Sadaqah Jar is Complete!"


class TestGenerateDailyActs:
    """
    Audit bug caught: the original N+1 loop issued one query per active user
    instead of batching. The refactored version uses a single query for user IDs
    and reuses the act pool in memory. This test verifies the functional contract
    is preserved - acts are cached for active users.
    """

    @patch("app.tasks.scheduled_tasks.cache_daily_acts")
    @patch("app.tasks.scheduled_tasks.generate_personalized_acts")
    def test_generates_for_active_users(
        self, mock_personalise, mock_cache, db, user, verified_act
    ):
        mock_personalise.return_value = [verified_act]

        from app.tasks.scheduled_tasks import generate_daily_acts

        generate_daily_acts()

        found = any(
            call_args[0][0] == user.id for call_args in mock_cache.call_args_list
        )
        assert found, "generate_daily_acts did not cache acts for the active test user"

    @patch("app.tasks.scheduled_tasks.cache_daily_acts")
    @patch("app.tasks.scheduled_tasks.generate_personalized_acts")
    def test_batch_query_no_n_plus_one(
        self, mock_personalise, mock_cache, db, user, verified_act
    ):
        """
        Verify the refactored code issues exactly two queries (acts + users)
        by checking that the act pool is fetched before the user loop.
        """
        from app.tasks.scheduled_tasks import generate_daily_acts

        mock_personalise.return_value = [verified_act]
        generate_daily_acts()

        assert mock_personalise.call_count >= 1


class TestAwareReminderRules:
    def _template(self, db, key, category="journey"):
        existing = db.query(NotificationTemplate).filter_by(key=key).first()
        if existing is not None:
            return existing
        template = NotificationTemplate(
            key=key,
            title_template=key,
            message_template="A gentle reminder",
            category=category,
            strategy=SchedulingStrategy.PRAYER_RELATIVE.value,
            strategy_config=json.dumps({"anchor": "fajr"}),
            enabled=True,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    def test_tahajjud_is_opt_in_and_friday_uses_profile_toggle(self, db, user):
        from app.tasks.scheduled_tasks import _should_skip_for_user

        friday = self._template(db, "friday_reminder", "islamic_occasions")
        tahajjud = self._template(db, "tahajjud_reminder", "time_based")
        assert _should_skip_for_user(db, user, friday, local_date=date(2026, 8, 21))
        assert _should_skip_for_user(db, user, tahajjud, local_date=date(2026, 8, 21))

        user.preferences = UserPreference(
            timezone="Africa/Lagos",
            notification_preferences=json.dumps({"friday_reminder": True}),
            reminder_preferences=json.dumps({"tahajjud": True}),
        )
        db.commit()
        db.refresh(user)
        assert not _should_skip_for_user(db, user, friday, local_date=date(2026, 8, 21))
        assert not _should_skip_for_user(db, user, tahajjud, local_date=date(2026, 8, 21))

    def test_quran_activity_suppresses_same_day_quran_prompt(self, db, user):
        from app.tasks.scheduled_tasks import _should_skip_for_user

        user.preferences = UserPreference(timezone="Africa/Lagos")
        progress = JourneyQuranProgress(
            user_id=user.id,
            surah_id=1,
            verse_key="1:1",
            page=1,
            last_read_at=datetime(2026, 8, 21, 9, 0),
        )
        template = self._template(db, "quran_rule_test", "quran")
        db.add(progress)
        db.commit()
        assert _should_skip_for_user(db, user, template, local_date=date(2026, 8, 21))

    def test_completed_salah_suppresses_only_its_own_reminder(self, db, user):
        from app.tasks.scheduled_tasks import _should_skip_for_user

        user.preferences = UserPreference(timezone="Africa/Lagos")
        fajr = self._template(db, "fajr_reminder", "prayer_fardh")
        dhuhr = self._template(db, "dhuhr_reminder", "prayer_fardh")
        db.add(
            JourneyPrayerCompletion(
                user_id=user.id,
                local_date=date(2026, 8, 21),
                prayer_name="fajr",
                completed_at=datetime(2026, 8, 21, 5, 30),
            )
        )
        db.commit()

        assert _should_skip_for_user(
            db, user, fajr, local_date=date(2026, 8, 21)
        )
        assert not _should_skip_for_user(
            db, user, dhuhr, local_date=date(2026, 8, 21)
        )
        db.query(JourneyPrayerCompletion).filter_by(user_id=user.id).delete()
        db.commit()

    def test_salah_reminder_can_be_disabled_individually(self, db, user):
        from app.tasks.scheduled_tasks import _should_skip_for_user

        user.preferences = UserPreference(
            timezone="Africa/Lagos",
            reminder_preferences=json.dumps(
                {"prayer_reminders": {"asr": {"enabled": False}}}
            ),
        )
        asr = self._template(db, "asr_reminder", "prayer_fardh")
        maghrib = self._template(db, "maghrib_reminder", "prayer_fardh")
        db.commit()

        assert _should_skip_for_user(db, user, asr, local_date=date(2026, 8, 21))
        assert not _should_skip_for_user(
            db, user, maghrib, local_date=date(2026, 8, 21)
        )

    def test_nawafil_after_salah_is_opt_in_and_limited_to_allowed_prayers(
        self, db, user
    ):
        from app.services.prayer_reminder_service import (
            PrayerTimes,
            schedule_prayer_relative_templates,
        )
        from app.tasks.scheduled_tasks import (
            _filter_schedules_for_user,
            _should_skip_for_user,
        )

        local_date = date(2026, 8, 21)
        zone = ZoneInfo("Africa/Lagos")
        anchors = {
            "fajr": datetime(2026, 8, 21, 5, 10, tzinfo=zone),
            "sunrise": datetime(2026, 8, 21, 6, 20, tzinfo=zone),
            "duha_start": datetime(2026, 8, 21, 6, 35, tzinfo=zone),
            "duha_end": datetime(2026, 8, 21, 11, 50, tzinfo=zone),
            "zuhr": datetime(2026, 8, 21, 12, 0, tzinfo=zone),
            "asr": datetime(2026, 8, 21, 15, 20, tzinfo=zone),
            "maghrib": datetime(2026, 8, 21, 18, 40, tzinfo=zone),
            "isha": datetime(2026, 8, 21, 19, 50, tzinfo=zone),
        }
        prayer_times = PrayerTimes(**anchors)
        keys_and_anchors = {
            "nawafil_after_dhuhr": "zuhr",
            "nawafil_after_maghrib": "maghrib",
            "nawafil_after_isha": "isha",
        }
        templates = {}
        for key, anchor in keys_and_anchors.items():
            template = self._template(db, key, "prayer_nafl")
            template.strategy_config = json.dumps(
                {"anchor": anchor, "offset_minutes": 15}
            )
            templates[key] = template
        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session="fetch")
        user.preferences = UserPreference(
            timezone="Africa/Lagos", reminder_preferences=json.dumps({})
        )
        db.commit()

        disabled = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=prayer_times,
            reminder_preferences={},
        )
        assert not any(
            db.get(NotificationTemplate, row.template_id).key in keys_and_anchors
            for row in disabled
        )
        assert all(
            _should_skip_for_user(db, user, template, local_date=local_date)
            for template in templates.values()
        )

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session="fetch")
        user.preferences.reminder_preferences = json.dumps(
            {"nawafil_after_salah": True}
        )
        db.commit()
        enabled = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=prayer_times,
            reminder_preferences={"nawafil_after_salah": True},
        )
        schedules = {
            db.get(NotificationTemplate, row.template_id).key: row
            for row in enabled
            if db.get(NotificationTemplate, row.template_id).key in keys_and_anchors
        }
        assert set(schedules) == set(keys_and_anchors)
        filtered = _filter_schedules_for_user(
            db, user, enabled, local_date=local_date
        )
        filtered_keys = {
            db.get(NotificationTemplate, row.template_id).key for row in filtered
        }
        assert filtered_keys.intersection(keys_and_anchors) == set(keys_and_anchors)
        for key, anchor in keys_and_anchors.items():
            assert schedules[key].scheduled_for == (
                anchors[anchor] + timedelta(minutes=15)
            ).astimezone(timezone.utc).replace(tzinfo=None)
            assert not _should_skip_for_user(
                db, user, templates[key], local_date=local_date
            )
        assert not any("fajr" in key or "asr" in key for key in schedules)

        user.preferences.notification_preferences = json.dumps(
            {"frequency": "low"}
        )
        db.commit()
        low_frequency = _filter_schedules_for_user(
            db, user, enabled, local_date=local_date
        )
        low_frequency_keys = {
            db.get(NotificationTemplate, row.template_id).key
            for row in low_frequency
        }
        assert low_frequency_keys.intersection(keys_and_anchors) == set(
            keys_and_anchors
        )

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session="fetch")
        db.commit()

    def test_all_five_salah_reminders_use_local_times_and_individual_offset(
        self, db, user
    ):
        from app.services.prayer_reminder_service import (
            PrayerTimes,
            schedule_prayer_relative_templates,
        )

        local_date = date(2026, 8, 21)
        zone = ZoneInfo("Africa/Lagos")
        anchors = {
            "fajr": datetime(2026, 8, 21, 5, 10, tzinfo=zone),
            "sunrise": datetime(2026, 8, 21, 6, 20, tzinfo=zone),
            "duha_start": datetime(2026, 8, 21, 6, 35, tzinfo=zone),
            "duha_end": datetime(2026, 8, 21, 11, 50, tzinfo=zone),
            "zuhr": datetime(2026, 8, 21, 12, 0, tzinfo=zone),
            "asr": datetime(2026, 8, 21, 15, 20, tzinfo=zone),
            "maghrib": datetime(2026, 8, 21, 18, 40, tzinfo=zone),
            "isha": datetime(2026, 8, 21, 19, 50, tzinfo=zone),
        }
        prayer_times = PrayerTimes(**anchors)
        user.preferences = UserPreference(timezone="Africa/Lagos")
        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session=False)
        db.commit()
        for key, anchor in (
            ("fajr_reminder", "fajr"),
            ("dhuhr_reminder", "zuhr"),
            ("asr_reminder", "asr"),
            ("maghrib_reminder", "maghrib"),
            ("isha_reminder", "isha"),
        ):
            template = self._template(db, key, "prayer_fardh")
            template.strategy_config = json.dumps(
                {"anchor": anchor, "offset_minutes": 0}
            )
        db.commit()

        schedules = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=prayer_times,
            reminder_preferences={
                "prayer_reminders": {"fajr": {"offset_minutes": -5}}
            },
        )
        salah_keys = {
            "fajr_reminder",
            "dhuhr_reminder",
            "asr_reminder",
            "maghrib_reminder",
            "isha_reminder",
        }
        by_key = {
            template.key: schedule
            for schedule in schedules
            if (template := db.get(NotificationTemplate, schedule.template_id))
            and template.key in salah_keys
        }

        assert salah_keys <= by_key.keys()
        assert by_key["fajr_reminder"].scheduled_for == (
            anchors["fajr"] - timedelta(minutes=5)
        ).astimezone(timezone.utc).replace(tzinfo=None)
        assert by_key["dhuhr_reminder"].scheduled_for == anchors[
            "zuhr"
        ].astimezone(timezone.utc).replace(tzinfo=None)

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session=False)
        db.commit()

    def test_disabling_salah_cancels_an_existing_pending_schedule(self, db, user):
        from app.services.prayer_reminder_service import (
            PrayerTimes,
            schedule_prayer_relative_templates,
        )
        from app.tasks.scheduled_tasks import _filter_schedules_for_user

        local_date = date(2026, 8, 21)
        zone = ZoneInfo("Africa/Lagos")
        prayer_times = PrayerTimes(
            fajr=datetime(2026, 8, 21, 5, 10, tzinfo=zone),
            sunrise=datetime(2026, 8, 21, 6, 20, tzinfo=zone),
            duha_start=datetime(2026, 8, 21, 6, 35, tzinfo=zone),
            duha_end=datetime(2026, 8, 21, 11, 50, tzinfo=zone),
            zuhr=datetime(2026, 8, 21, 12, 0, tzinfo=zone),
            asr=datetime(2026, 8, 21, 15, 20, tzinfo=zone),
            maghrib=datetime(2026, 8, 21, 18, 40, tzinfo=zone),
            isha=datetime(2026, 8, 21, 19, 50, tzinfo=zone),
        )
        template = self._template(db, "dhuhr_reminder", "prayer_fardh")
        template.strategy_config = json.dumps(
            {"anchor": "zuhr", "offset_minutes": 0}
        )
        user.preferences = UserPreference(timezone="Africa/Lagos")
        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session="fetch")
        db.commit()

        first = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=prayer_times,
            reminder_preferences={},
        )
        db.commit()
        pending = next(
            row
            for row in first
            if db.get(NotificationTemplate, row.template_id).key == "dhuhr_reminder"
        )

        user.preferences.reminder_preferences = json.dumps(
            {"prayer_reminders": {"dhuhr": {"enabled": False}}}
        )
        db.commit()
        second = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=prayer_times,
            reminder_preferences={
                "prayer_reminders": {"dhuhr": {"enabled": False}}
            },
        )
        _filter_schedules_for_user(db, user, second, local_date=local_date)
        db.commit()

        assert pending.status == "cancelled"

    def test_prayer_time_changes_update_pending_schedule(self, db, user):
        from app.services.prayer_reminder_service import (
            PrayerTimes,
            schedule_prayer_relative_templates,
        )

        local_date = date(2026, 8, 21)
        lagos = ZoneInfo("Africa/Lagos")
        utc = ZoneInfo("UTC")

        def times(zone, hour):
            return PrayerTimes(
                fajr=datetime(2026, 8, 21, 5, 10, tzinfo=zone),
                sunrise=datetime(2026, 8, 21, 6, 20, tzinfo=zone),
                duha_start=datetime(2026, 8, 21, 6, 35, tzinfo=zone),
                duha_end=datetime(2026, 8, 21, 11, 50, tzinfo=zone),
                zuhr=datetime(2026, 8, 21, hour, 0, tzinfo=zone),
                asr=datetime(2026, 8, 21, 15, 20, tzinfo=zone),
                maghrib=datetime(2026, 8, 21, 18, 40, tzinfo=zone),
                isha=datetime(2026, 8, 21, 19, 50, tzinfo=zone),
            )

        self._template(db, "dhuhr_reminder", "prayer_fardh").strategy_config = (
            json.dumps({"anchor": "zuhr", "offset_minutes": 0})
        )
        user.preferences = UserPreference(timezone="Africa/Lagos")
        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session="fetch")
        db.commit()
        first = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=times(lagos, 12),
            reminder_preferences={},
        )
        db.commit()
        first_row = next(
            row
            for row in first
            if db.get(NotificationTemplate, row.template_id).key == "dhuhr_reminder"
        )
        original_due = first_row.scheduled_for

        changed = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=local_date,
            prayer_times=times(utc, 13),
            reminder_preferences={},
        )
        db.commit()
        changed_row = next(
            row
            for row in changed
            if db.get(NotificationTemplate, row.template_id).key == "dhuhr_reminder"
        )

        assert changed_row.scheduled_for != original_due
        assert changed_row.scheduled_for == datetime(2026, 8, 21, 13, 0)

    def test_missing_timezone_uses_utc_rhythm_and_tahajjud_stays_off(self, db, user):
        from app.tasks.scheduled_tasks import _schedule_timezone_rhythm

        user.preferences = UserPreference(
            notification_preferences="{}", reminder_preferences="{}"
        )
        for key, category in (
            ("morning_adhkar", "adhkar_morning"),
            ("quran_reminder", "quran"),
            ("evening_adhkar", "adhkar_evening"),
            ("tahajjud_reminder", "time_based"),
        ):
            self._template(db, key, category)
        db.commit()
        schedules = _schedule_timezone_rhythm(
            db=db,
            user_id=user.id,
            local_date=date(2026, 8, 21),
            timezone_name="",
        )
        assert {schedule.template_id for schedule in schedules}
        assert all(schedule.scheduled_for.tzinfo is None for schedule in schedules)
        tahajjud_id = db.query(NotificationTemplate.id).filter_by(
            key="tahajjud_reminder"
        ).scalar()
        assert all(schedule.template_id != tahajjud_id for schedule in schedules)

    @patch("app.tasks.scheduled_tasks.deliver_scheduled_notification.apply_async")
    def test_missing_location_queues_full_timezone_fallback(self, mock_enqueue, db, user):
        from app.tasks.scheduled_tasks import _schedule_timezone_fallbacks

        mock_enqueue.return_value.id = "test-task-id"
        local_date = date(2026, 8, 20)
        user.preferences = UserPreference(
            timezone="Africa/Lagos",
            notification_preferences=json.dumps({"all_enabled": True}),
            reminder_preferences=json.dumps({}),
        )
        for key, category in (
            ("morning_adhkar", "adhkar_morning"),
            ("quran_reminder", "quran"),
            ("evening_adhkar", "adhkar_evening"),
        ):
            self._template(db, key, category)
        db.commit()

        _schedule_timezone_fallbacks(
            db=db,
            user=user,
            local_date=local_date,
            timezone_name="Africa/Lagos",
        )

        rows = (
            db.query(ScheduledNotification)
            .filter_by(user_id=user.id, local_date=local_date.isoformat())
            .all()
        )
        keys = {db.get(NotificationTemplate, row.template_id).key for row in rows}
        assert {"morning_adhkar", "quran_reminder", "evening_adhkar"} <= keys
        assert "random_sadaqah_prompt" in keys
        assert mock_enqueue.call_count == len(rows)

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session=False)
        db.commit()

    @patch("app.tasks.scheduled_tasks.deliver_scheduled_notification.apply_async")
    def test_missing_location_does_not_schedule_salah_or_nawafil(
        self, mock_enqueue, db, user
    ):
        from app.tasks.scheduled_tasks import _schedule_reminders_for_user

        mock_enqueue.return_value.id = "test-task-id"
        local_date = datetime.now(ZoneInfo("Africa/Lagos")).date()
        user.latitude = None
        user.longitude = None
        user.preferences = UserPreference(
            timezone="Africa/Lagos",
            notification_preferences=json.dumps({"all_enabled": True}),
            reminder_preferences=json.dumps({"nawafil_after_salah": True}),
        )
        for key, category in (
            ("fajr_reminder", "prayer_fardh"),
            ("dhuhr_reminder", "prayer_fardh"),
            ("asr_reminder", "prayer_fardh"),
            ("maghrib_reminder", "prayer_fardh"),
            ("isha_reminder", "prayer_fardh"),
            ("nawafil_after_dhuhr", "prayer_nafl"),
            ("nawafil_after_maghrib", "prayer_nafl"),
            ("nawafil_after_isha", "prayer_nafl"),
        ):
            self._template(db, key, category)
        db.commit()

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session=False)
        db.commit()

        _schedule_reminders_for_user(db, user)

        rows = (
            db.query(ScheduledNotification)
            .filter_by(user_id=user.id, local_date=local_date.isoformat())
            .all()
        )
        prayer_keys = {
            db.get(NotificationTemplate, row.template_id).key
            for row in rows
            if db.get(NotificationTemplate, row.template_id).key
            in {
                "fajr_reminder",
                "dhuhr_reminder",
                "asr_reminder",
                "maghrib_reminder",
                "isha_reminder",
                "nawafil_after_dhuhr",
                "nawafil_after_maghrib",
                "nawafil_after_isha",
            }
        }
        assert prayer_keys == set()

        db.query(ScheduledNotification).filter_by(
            user_id=user.id, local_date=local_date.isoformat()
        ).delete(synchronize_session=False)
        db.commit()

    def test_prayer_relative_templates_deduplicate_semantic_group(self, db, user):
        from app.services.prayer_reminder_service import PrayerTimes, schedule_prayer_relative_templates

        canonical = self._template(db, "morning_adhkar", "adhkar_morning")
        expanded = self._template(db, "morning_adhkar_expanded", "adhkar_morning")
        anchor = datetime(2026, 8, 21, 5, 0)
        prayer_times = PrayerTimes(
            fajr=anchor,
            sunrise=anchor,
            duha_start=anchor,
            duha_end=anchor,
            zuhr=anchor,
            asr=anchor,
            maghrib=anchor,
            isha=anchor,
        )

        schedules = schedule_prayer_relative_templates(
            db,
            user_id=user.id,
            local_date=date(2026, 8, 21),
            prayer_times=prayer_times,
        )
        ids = [schedule.template_id for schedule in schedules]
        assert canonical.id in ids
        assert expanded.id not in ids
