#!/usr/bin/env python
"""
Seed script for Mizan database.

Covers every persistent user-state table in the codebase:
  - Legacy: users, jars, sadaqah_logs, user_streaks, badges, user_badges, evidence
  - New sadaqah: activity_completions, activity_sessions, activity_streaks
  - Journey: reflections, adhkar_favorites, adhkar_progress
  - Notifications
  - Family: families, members, goals, prayer_requests, reflections, activities, settings
  - Books: catalog entries (admin-managed)

NOTE: There is NO backend model for per-user book reading progress
("Continue reading" is currently a UI-only feature with no persistence).
Do not invent one — flag for backend work.

Usage:
    python -m app.seed.seed
    python -m app.seed.seed --clean
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal

# Legacy models
from app.models.badge import Badge
from app.models.charity import Charity
from app.models.evidence import Evidence
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct, SadaqahCategory
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User, Role, UserMode
from app.models.user_badge import UserBadge
from app.models.user_streak import UserStreak

# New domain models
from app.users.models import UserPreference
from app.sadaqah.models import (
    ActivityCompletion,
    ActivitySession,
    ActivityStreak,
    ActivityType,
    ActivityContext,
)
from app.family.models import (
    Family,
    FamilyMember,
    FamilyGoal,
    PrayerRequest,
    PrayerRequestResponse,
    FamilyReflection,
    ReflectionEncouragement,
    FamilyActivity,
    FamilySettings,
    FamilyInvitation,
    FamilyRole,
    EventType,
    PrayerResponseType,
    EncouragementType,
)
from app.journey.models import (
    JourneyReflection,
    JourneyAdhkarProgress,
    JourneyAdhkarFavorite,
)
from app.notifications.models import Notification, NotificationTemplate, SchedulingStrategy
from app.books.models import Book, BookChapter


def _utcnow() -> datetime:
    return datetime.utcnow()


class DatabaseSeeder:
    """Manages database seeding with transaction rollback."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        tables = [
            ReflectionEncouragement,  # family
            PrayerRequestResponse,
            FamilyActivity,
            FamilyReflection,
            PrayerRequest,
            FamilyGoal,
            FamilyInvitation,
            FamilyMember,
            FamilySettings,
            Family,
            BookChapter,
            Book,
            JourneyAdhkarFavorite,
            JourneyAdhkarProgress,
            JourneyReflection,
            Notification,
            ActivitySession,
            ActivityCompletion,
            ActivityStreak,
            UserPreference,
            UserBadge,
            Badge,
            SadaqahLog,
            Jar,
            UserStreak,
            Evidence,
            SadaqahAct,
            Charity,
            User,
        ]
        for table in tables:
            self.db.query(table).delete()
        self.db.commit()
        print("[OK] Database cleared")

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def seed_users(self) -> list[User]:
        seed_profiles = [
            ("summie", "summie@admin.com", "ADMIN"),
            ("fatima", "fatima@example.com", "USER"),
            ("ali", "ali@example.com", "USER"),
            ("aisha", "aisha@example.com", "USER"),
            ("omar", "omar@example.com", "USER"),
            ("zahra", "zahra@example.com", "USER"),
            ("hassan", "hassan@example.com", "USER"),
            ("leila", "leila@example.com", "USER"),
            ("karim", "karim@example.com", "USER"),
            ("amira", "amira@example.com", "USER"),
        ]

        users: list[User] = []
        for username, email, role in seed_profiles:
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                user.username = username
                user.hashed_password = hash_password("password123")
                user.role = Role[role]
                user.created_at = _utcnow() - timedelta(days=random.randint(1, 90))
            else:
                user = User(
                    email=email,
                    username=username,
                    hashed_password=hash_password("password123"),
                    role=Role[role],
                    created_at=_utcnow() - timedelta(days=random.randint(1, 90)),
                )
                self.db.add(user)
            users.append(user)

        self.db.commit()
        print(f"[OK] Created/updated {len(users)} users")
        return users

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def seed_preferences(self, users: list[User]) -> None:
        for user in users:
            pref = UserPreference(
                user_id=user.id,
                theme="light",
                language="en",
                selected_mode=random.choice([UserMode.PERSONAL, UserMode.FAMILY, UserMode.BOTH]),
                timezone="UTC",
                notification_preferences='{"push": true, "email": false}',
                reminder_preferences='{"friday": true}',
                accessibility_preferences='{"font_scale": 1.0}',
                privacy_preferences='{"analytics": false}',
            )
            self.db.add(pref)
        self.db.commit()
        print(f"[OK] Created preferences for {len(users)} users")

    # ------------------------------------------------------------------
    # Legacy streaks (user_streaks table)
    # ------------------------------------------------------------------
    def seed_legacy_streaks(self, users: list[User]) -> None:
        streak_configs = [
            (0, 0, _utcnow() - timedelta(days=45)),        # broken streak
            (12, 18, _utcnow() - timedelta(days=1)),       # active strong
            (7, 14, _utcnow() - timedelta(days=0)),        # active medium
            (3, 10, _utcnow() - timedelta(days=2)),        # active weak
            (0, 5, _utcnow() - timedelta(days=30)),        # broken
        ]
        for idx, user in enumerate(users[:5]):
            current, longest, last = streak_configs[idx]
            streak = UserStreak(
                user_id=user.id,
                current_streak=current,
                longest_streak=longest,
                last_completed_date=last.date(),
            )
            self.db.add(streak)
        self.db.commit()
        print("[OK] Created legacy user streaks")

    # ------------------------------------------------------------------
    # New activity streaks (activity_streaks table)
    # ------------------------------------------------------------------
    def seed_activity_streaks(self, users: list[User]) -> None:
        types = [ActivityType.DHIKR, ActivityType.PRAYER, ActivityType.KINDNESS, ActivityType.FOOD]
        for user in users:
            for act_type in types:
                current = random.choice([0, 3, 7, 12, 15])
                longest = max(current, random.randint(5, 25))
                last = _utcnow() - timedelta(days=random.randint(0, 20 if current > 0 else 60))
                streak = ActivityStreak(
                    user_id=user.id,
                    activity_type=act_type,
                    current_streak=current,
                    longest_streak=longest,
                    last_completed_at=last if current > 0 else None,
                )
                self.db.add(streak)
        self.db.commit()
        print(f"[OK] Created activity streaks for {len(users)} users")

    # ------------------------------------------------------------------
    # Legacy jars
    # ------------------------------------------------------------------
    def seed_jars(self, users: list[User]) -> None:
        # user[0] = admin: completed jar
        completed_jar = Jar(
            user_id=users[0].id,
            current_stars=33,
            capacity=33,
            completed_at=_utcnow() - timedelta(days=10),
        )
        self.db.add(completed_jar)

        # user[1] = mid-progress jar
        mid_jar = Jar(
            user_id=users[1].id,
            current_stars=15,
            capacity=33,
            completed_at=None,
        )
        self.db.add(mid_jar)

        # user[2] = empty jar, just started
        empty_jar = Jar(
            user_id=users[2].id,
            current_stars=2,
            capacity=33,
            completed_at=None,
        )
        self.db.add(empty_jar)

        # Others: random legacy jars
        for user in users[3:]:
            stars = random.randint(0, 33)
            completed = _utcnow() - timedelta(days=random.randint(1, 60)) if stars >= 33 else None
            jar = Jar(
                user_id=user.id,
                current_stars=stars,
                capacity=33,
                completed_at=completed,
            )
            self.db.add(jar)

        self.db.commit()
        print("[OK] Created legacy jars")

    # ------------------------------------------------------------------
    # Sadaqah acts + evidence
    # ------------------------------------------------------------------
    def seed_acts(self) -> list[SadaqahAct]:
        acts_data = [
            ("Say SubhanAllah 100 times", "dhikr", 1, 1),
            ("Say Alhamdulillah 100 times", "dhikr", 1, 1),
            ("Make dua for parents", "dhikr", 2, 2),
            ("Read Quran for 10 minutes", "dhikr", 2, 2),
            ("Learn a new Surah", "dhikr", 3, 3),
            ("Give Sadaqah to someone in need", "donation", 2, 2),
            ("Feed a poor person", "donation", 2, 2),
            ("Smile at someone with intention", "kindness", 1, 1),
            ("Help a neighbour", "community", 2, 2),
            ("Remove harm from the road", "community", 1, 1),
            ("Pray two rakah Nafil", "prayer", 2, 2),
            ("Attend Jumu'ah prayer", "prayer", 2, 3),
            ("Teach someone about Islam", "knowledge", 3, 2),
            ("Daily affirmation", "general", 1, 1),
        ]

        evidence_data = [
            ("HADITH", "Sahih Muslim 2693", "Sahih", "SubhanAllah hadith text", "English translation"),
            ("HADITH", "Sahih Muslim 2692", "Sahih", "Alhamdulillah hadith text", "English translation"),
            ("QURAN", "Al-Isra 17:24", "Quranic", "Arabic verse", "English translation"),
            ("HADITH", "Sahih al-Bukhari", "Sahih", "Quran reading hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari 6405", "Sahih", "La ilaha hadith", "English translation"),
            ("QURAN", "Al-Baqarah 2:261", "Quranic", "Charity verse", "English translation"),
            ("HADITH", "Sahih al-Bukhari", "Sahih", "Feeding poor hadith", "English translation"),
            ("HADITH", "Jami at-Tirmidhi 1956", "Sahih", "Smile hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari 6016", "Sahih", "Neighbor hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari 2989", "Sahih", "Remove harm hadith", "English translation"),
            ("HADITH", "Sahih Muslim", "Sahih", "Nafil prayer hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari", "Sahih", "Jumu'ah hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari 61", "Sahih", "Teach Islam hadith", "English translation"),
            ("HADITH", "Sahih al-Bukhari", "Sahih", "Affirmation hadith", "English translation"),
        ]

        acts: list[SadaqahAct] = []
        for idx, (title, category, difficulty, reward) in enumerate(acts_data):
            act = SadaqahAct(
                title=title,
                description=title,
                category=SadaqahCategory(category),
                difficulty=difficulty,
                reward_weight=reward,
                verified=True,
                is_ramadan_only=False,
                ramadan_multiplier=1,
            )
            self.db.add(act)
            acts.append(act)

            src_type, ref, grade, arabic, english = evidence_data[idx]
            ev = Evidence(
                act=act,
                source_type=src_type,
                reference=ref,
                grade=grade,
                arabic_text=arabic,
                english_text=english,
                is_verified=True,
            )
            self.db.add(ev)

        self.db.commit()
        print(f"[OK] Created {len(acts)} acts with evidence")
        return acts

    # ------------------------------------------------------------------
    # Legacy sadaqah logs
    # ------------------------------------------------------------------
    def seed_sadaqah_logs(self, users: list[User], acts: list[SadaqahAct]) -> None:
        log_count = 0
        used = set()
        for user in users:
            for _ in range(random.randint(10, 40)):
                act = random.choice(acts)
                log_date = date.today() - timedelta(days=random.randint(0, 60))
                key = (user.id, act.id, log_date)
                if key in used:
                    continue
                used.add(key)
                multiplier = act.reward_weight or 1
                is_friday = log_date.weekday() == 4
                if is_friday:
                    multiplier *= 2
                log = SadaqahLog(
                    user_id=user.id,
                    act_id=act.id,
                    date=log_date,
                    stars_earned=int(multiplier),
                    friday_boost=is_friday,
                    ramadan_bonus=False,
                    created_at=datetime.combine(log_date, datetime.min.time()),
                )
                self.db.add(log)
                log_count += 1
        self.db.commit()
        print(f"[OK] Created {log_count} sadaqah logs")

    # ------------------------------------------------------------------
    # New activity completions
    # ------------------------------------------------------------------
    def seed_activity_completions(self, users: list[User]) -> None:
        act_types = list(ActivityType)
        contexts = list(ActivityContext)
        total = 0
        for user in users:
            for _ in range(random.randint(8, 30)):
                act_type = random.choice(act_types)
                context = random.choice(contexts)
                completed = _utcnow() - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
                comp = ActivityCompletion(
                    user_id=user.id,
                    activity_type=act_type,
                    context=context,
                    note=None,
                    family_id=None,
                    completed_at=completed,
                    stars_earned=random.randint(1, 3),
                    friday_boost=(completed.weekday() == 4),
                    ramadan_bonus=False,
                )
                self.db.add(comp)
                total += 1
        self.db.commit()
        print(f"[OK] Created {total} activity completions")

    # ------------------------------------------------------------------
    # New activity sessions (continuous acts)
    # ------------------------------------------------------------------
    def seed_activity_sessions(self, users: list[User]) -> None:
        continuous = [ActivityType.PRAYER, ActivityType.DHIKR, ActivityType.TIME]
        total = 0
        for user in users:
            for _ in range(random.randint(2, 8)):
                act_type = random.choice(continuous)
                started = _utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 12))
                duration = random.randint(300, 3600)
                session = ActivitySession(
                    user_id=user.id,
                    activity_type=act_type,
                    started_at=started,
                    ended_at=started + timedelta(seconds=duration),
                    duration_seconds=duration,
                    context=random.choice(list(ActivityContext)),
                    family_id=None,
                )
                self.db.add(session)
                total += 1
        self.db.commit()
        print(f"[OK] Created {total} activity sessions")

    # ------------------------------------------------------------------
    # Family domain
    # ------------------------------------------------------------------
    def seed_families(self, users: list[User]) -> None:
        # Active family: users[0] (admin) + users[1] + users[2]
        active_family = Family(
            name="Al-Rahman Family",
            cover_icon="🌿",
            invite_code="ALRAHMAN-2026",
            created_by=users[0].id,
            created_at=_utcnow() - timedelta(days=60),
        )
        self.db.add(active_family)
        self.db.flush()

        members = [
            FamilyMember(family_id=active_family.id, user_id=users[0].id, role=FamilyRole.OWNER),
            FamilyMember(family_id=active_family.id, user_id=users[1].id, role=FamilyRole.ADMIN),
            FamilyMember(family_id=active_family.id, user_id=users[2].id, role=FamilyRole.MEMBER),
        ]
        for m in members:
            self.db.add(m)

        self.db.add(FamilySettings(family_id=active_family.id, notification_preferences={}, version=1))

        # Goal
        goal = FamilyGoal(
            family_id=active_family.id,
            created_by=users[0].id,
            title="Ramadan Good Deeds",
            subtitle="100 acts as a family",
            acts_target=100,
            acts_done=34,
            completed_at=None,
            is_archived=False,
            version=1,
        )
        self.db.add(goal)

        # Prayer request
        pr = PrayerRequest(
            family_id=active_family.id,
            author_id=users[1].id,
            text="Please pray for my mother's health",
            is_answered=False,
            is_private=False,
        )
        self.db.add(pr)
        self.db.flush()

        resp = PrayerRequestResponse(
            prayer_request_id=pr.id,
            user_id=users[2].id,
            response_type=PrayerResponseType.AMEEN,
        )
        self.db.add(resp)

        # Reflection
        refl = FamilyReflection(
            family_id=active_family.id,
            author_id=users[0].id,
            text="Grateful for this family and our shared journey.",
        )
        self.db.add(refl)
        self.db.flush()

        enc = ReflectionEncouragement(
            reflection_id=refl.id,
            user_id=users[1].id,
            encouragement_type=EncouragementType.MAY_ALLAH_ACCEPT,
        )
        self.db.add(enc)

        # Activities
        for event in [
            EventType.FAMILY_CREATED,
            EventType.MEMBER_JOINED,
            EventType.GOAL_CREATED,
            EventType.PRAYER_REQUEST_CREATED,
            EventType.REFLECTION_SHARED,
        ]:
            act = FamilyActivity(
                family_id=active_family.id,
                actor_id=users[0].id,
                event_type=event,
                extra={"note": event.value},
            )
            self.db.add(act)

        # Archived (soft-deleted) family for history
        archived = Family(
            name="Old Family Jar",
            cover_icon="🕊️",
            invite_code="OLD-2025-ARCHIVED",
            created_by=users[3].id,
            created_at=_utcnow() - timedelta(days=120),
            deleted_at=_utcnow() - timedelta(days=15),
        )
        self.db.add(archived)

        self.db.commit()
        print("[OK] Created families with members, goals, prayers, reflections")

    # ------------------------------------------------------------------
    # Journey reflections
    # ------------------------------------------------------------------
    def seed_journey_reflections(self, users: list[User]) -> None:
        moods = ["grateful", "peaceful", "reflective", "hopeful", "humbled"]
        for user in users[:5]:
            for _ in range(random.randint(1, 3)):
                refl = JourneyReflection(
                    user_id=user.id,
                    title=random.choice(["Blessings of today", "A moment of peace", "Lessons from the Quran", "Patience in hardship"]),
                    body="A personal reflection on faith, gratitude, and growth.",
                    mood=random.choice(moods),
                    is_private=random.choice([True, False]),
                    date=_utcnow() - timedelta(days=random.randint(0, 30)),
                )
                self.db.add(refl)
        self.db.commit()
        print("[OK] Created journey reflections")

    # ------------------------------------------------------------------
    # Journey adhkar favorites + progress
    # ------------------------------------------------------------------
    def seed_journey_adhkar(self, users: list[User]) -> None:
        adhkar_ids = list(range(1, 11))
        for user in users[:6]:
            fav_ids = random.sample(adhkar_ids, k=random.randint(1, 4))
            for aid in fav_ids:
                self.db.add(JourneyAdhkarFavorite(user_id=user.id, adhkar_id=aid))
            for aid in random.sample(adhkar_ids, k=random.randint(2, 5)):
                self.db.add(JourneyAdhkarProgress(user_id=user.id, adhkar_id=aid, count=random.randint(0, 33)))
        self.db.commit()
        print("[OK] Created adhkar favorites and progress")

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def seed_notifications(self, users: list[User]) -> None:
        categories = ["family", "journey", "prayer", "adhkar", "reading", "reflection", "charity", "announcements"]
        for user in users:
            for _ in range(random.randint(3, 8)):
                notif = Notification(
                    user_id=user.id,
                    category=random.choice(categories),
                    title=random.choice(["Friday reminder", "Family update", "New reflection", "Prayer request"]),
                    message="A gentle notification for your journey.",
                    action=None,
                    is_read=random.choice([True, False]),
                    created_at=_utcnow() - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23)),
                )
                self.db.add(notif)
        self.db.commit()
        print(f"[OK] Created notifications for {len(users)} users")

    def seed_notification_templates(self) -> None:
        """Seed editable reminder definitions; runtime tasks contain no wording."""
        templates = [
            ("morning_adhkar", "Morning adhkar", "{arabic}\n{translation}\n{source} · Repeat {repeat_count}×", "adhkar", {"anchor": "fajr", "offset_minutes": 30, "content_source": "morning_adhkar"}),
            ("evening_adhkar", "Evening adhkar", "{arabic}\n{translation}\n{source} · Repeat {repeat_count}×", "adhkar", {"anchor": "asr", "offset_minutes": 30, "content_source": "evening_adhkar"}),
            ("salatul_duha", "Salatul Duha", "A gentle window for two rak'ahs of Duha is open.", "prayer", {"anchor": "duha_start", "offset_minutes": 15}),
            ("witr_reminder", "Remember Witr", "Complete your night with Witr before sleep.", "prayer", {"anchor": "isha", "offset_minutes": 45}),
            ("daily_sadaqah", "Today's sadaqah", "{act_title}: {act_description}", "charity", {"anchor": "zuhr", "offset_minutes": 30, "content_source": "personalized_sadaqah"}),
            ("quran_reminder", "A moment with the Quran", "Open the Quran today, even for a few verses, and reflect on what you read.", "reading", {"anchor": "maghrib", "offset_minutes": 30}),
            ("friday_reminder", "Friday reminder", "{message}", "islamic_occasions", {"anchor": "zuhr", "offset_minutes": -30, "days_of_week": [4], "content_source": "rotating_messages", "messages": ["Send abundant salawat upon the Prophet today.", "Read Surah Al-Kahf - it is a light between two Fridays.", "Give charity today - Friday charity is specially multiplied.", "Make dua in the last hour after Asr - it is the hour of acceptance.", "Reach out to a relative to strengthen family ties."]}),
        ]
        created = 0
        for key, title, message, category, config in templates:
            if self.db.query(NotificationTemplate).filter(NotificationTemplate.key == key).first():
                continue
            self.db.add(NotificationTemplate(
                key=key,
                title_template=title,
                message_template=message,
                category=category,
                strategy=SchedulingStrategy.PRAYER_RELATIVE.value,
                strategy_config=json.dumps(config),
                enabled=True,
            ))
            created += 1
        self.db.commit()
        print(f"[OK] Created {created} notification templates")

    # ------------------------------------------------------------------
    # Admin badges
    # ------------------------------------------------------------------
    def seed_badges(self, users: list[User]) -> None:
        badge_names = [
            "Generous Soul",
            "Streak Keeper",
            "Community Champion",
            "Friday Warrior",
            "Global Top 10",
        ]
        badges: list[Badge] = []
        for name in badge_names:
            b = Badge(name=name, description=f"Earned for: {name}")
            self.db.add(b)
            badges.append(b)
        self.db.commit()

        for user in users:
            selected = random.sample(badges, k=random.randint(0, len(badges)))
            for badge in selected:
                self.db.add(UserBadge(user_id=user.id, badge_id=badge.id))
        self.db.commit()
        print(f"[OK] Created {len(badges)} badges and assigned to users")

    # ------------------------------------------------------------------
    # Books (catalog — admin-managed, no per-user progress table exists)
    # ------------------------------------------------------------------
    def seed_books(self) -> None:
        books_data = [
            {
                "title": "Stories of the Prophets",
                "author": "Ibn Kathir",
                "description": "Stories of the prophets from Adam to Muhammad (PBUH), drawn from the Quran and authentic hadith.",
                "cover_url": None,
                "category": "seerah",
                "language": "en",
                "published": True,
                "sort_order": 1,
                "chapters": [
                    (1, "The Story of Adam (AS)", "In the beginning, Allah created Adam from clay and breathed life into him...", 8),
                    (2, "The Story of Nuh (AS)", "Nuh called his people to worship Allah alone for 950 years...", 10),
                    (3, "The Story of Ibrahim (AS)", "Ibrahim broke the idols and called his father and people to the truth...", 12),
                ],
            },
            {
                "title": "Purification of the Heart",
                "author": "Hamza Yusuf",
                "description": "Signs, symptoms, and cures of the diseases of the heart.",
                "cover_url": None,
                "category": "character",
                "language": "en",
                "published": True,
                "sort_order": 2,
                "chapters": [
                    (1, "The Mirror of the Heart", "The heart is like a mirror — it must be polished to reflect the truth...", 6),
                    (2, "Envy and Jealousy", "Envy consumes good deeds like fire consumes wood...", 7),
                    (3, "Anger and Its Cure", "The Prophet (PBUH) taught that the strong person controls their anger...", 8),
                ],
            },
            {
                "title": "Riyad as-Salihin",
                "author": "Imam Nawawi",
                "description": "A foundational collection of hadith covering ethics and spirituality.",
                "cover_url": None,
                "category": "hadith",
                "language": "en",
                "published": True,
                "sort_order": 3,
                "chapters": [
                    (1, "On the Excellence of Knowledge", "The Prophet (PBUH) said: 'Whoever travels a path seeking knowledge...'", 5),
                    (2, "On Good Character", "The best of you are those with the best character...", 6),
                    (3, "On Praying at Night", "The best prayer after the obligatory prayers is prayer at night...", 7),
                ],
            },
        ]

        for b in books_data:
            book = Book(
                title=b["title"],
                author=b["author"],
                description=b["description"],
                cover_url=b.get("cover_url"),
                category=b["category"],
                language=b["language"],
                published=b["published"],
                sort_order=b["sort_order"],
            )
            self.db.add(book)
            self.db.flush()

            for chapter_num, title, content, minutes in b["chapters"]:
                ch = BookChapter(
                    book_id=book.id,
                    chapter_number=chapter_num,
                    title=title,
                    content=content,
                    reading_time_minutes=minutes,
                )
                self.db.add(ch)

        self.db.commit()
        print("[OK] Created books and chapters")
        print("[NOTE] No per-user book reading progress table exists yet — 'Continue reading' is UI-only")

    # ------------------------------------------------------------------
    # Legacy charities
    # ------------------------------------------------------------------
    def seed_charities(self) -> None:
        charities_data = [
            ("Islamic Relief", "Providing humanitarian aid globally", "https://www.islamic-relief.org", "humanitarian", True),
            ("IRUSA", "Supporting Muslim communities in USA", "https://irusa.org", "community", True),
            ("Muslim Hands", "Emergency relief and development", "https://muslimhands.org.uk", "humanitarian", True),
            ("Zakat Foundation", "Zakat distribution and social services", "https://www.zakat.org", "zakat", True),
        ]
        for name, desc, url, cat, featured in charities_data:
            c = Charity(name=name, description=desc, website_url=url, category=cat, is_verified=True, is_active=True, is_featured=featured)
            self.db.add(c)
        self.db.commit()
        print("[OK] Created charities")

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run(self, clean: bool = False) -> None:
        try:
            if clean:
                self.clear_all()

            print("\n[SEED] Starting database seeding...\n")
            users = self.seed_users()
            self.seed_preferences(users)
            self.seed_legacy_streaks(users)
            self.seed_activity_streaks(users)
            self.seed_jars(users)
            acts = self.seed_acts()
            self.seed_charities()
            self.seed_sadaqah_logs(users, acts)
            self.seed_activity_completions(users)
            self.seed_activity_sessions(users)
            self.seed_families(users)
            self.seed_journey_reflections(users)
            self.seed_journey_adhkar(users)
            self.seed_notifications(users)
            self.seed_notification_templates()
            self.seed_badges(users)
            self.seed_books()

            print("\n[OK] Database seeding completed successfully!\n")
            print("[DATA] Summary:")
            print(f"   • {len(users)} users (admin: summie@admin.com / password123)")
            print(f"   • Legacy jars: completed (1), mid-progress (1), varied (rest)")
            print(f"   • Streaks: broken (2), active (multiple), varying lengths")
            print(f"   • 1 active family (3 members), 1 archived family")
            print(f"   • Remaining users: solo mode")
            print(f"   • Journey reflections, adhkar favorites/progress seeded")
            print(f"   • Notifications, badges, activities, books seeded")
            print()

        except Exception as e:
            print(f"\n[ERROR] Seeding failed: {str(e)}")
            self.db.rollback()
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            self.db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Mizan database")
    parser.add_argument("--clean", action="store_true", help="Clear and reseed the database")
    args = parser.parse_args()

    db = SessionLocal()
    seeder = DatabaseSeeder(db)
    seeder.run(clean=args.clean)


if __name__ == "__main__":
    main()
