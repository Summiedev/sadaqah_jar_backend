"""Journey domain service layer."""

from datetime import date, datetime, timezone

from sqlalchemy import Integer, String, Text, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.journey import repository as repo
from app.journey.models import (
    JourneyAdhkarProgress,
    JourneyPrayerCompletion,
    JourneyQuranProgress,
    JourneyReadingProgress,
    JourneyReflection,
)
from app.journey.exceptions import (
    FavoriteConflictException,
    FavoriteNotFoundException,
    ProgressNotFoundException,
    ReflectionNotFoundException,
)
from app.journey.schemas import (
    ReadingProgressResponse,
    ReflectionCreate,
    ReflectionUpdate,
    ReflectionResponse,
    AdhkarProgressResponse,
    AdhkarFavoriteResponse,
    QuranProgressPayload,
    QuranProgressResponse,
    PrayerCompletionState,
    PrayerCompletionUpdate,
    JourneyHistoryItem,
    JourneyHistoryPage,
)
from app.models.sadaqah_act import SadaqahAct
from app.models.sadaqah_log import SadaqahLog
from app.sadaqah.models import ActivityCompletion
from app.goals.models import UserGoal
from app.family.models import FamilyActivity


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stored_enum_value(value: object, values: dict[str, str] | None = None) -> str:
    """Normalize SQLAlchemy's non-native enum names to public enum values."""
    raw = str(value or "")
    if values and raw in values:
        return values[raw]
    if raw.startswith("ActivityType.") or raw.startswith("ActivityContext."):
        raw = raw.split(".", 1)[1]
    return raw.lower()


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


def list_reflections(
    db: Session, user_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[ReflectionResponse], int]:
    reflections, total = repo.list_reflections(db, user_id, limit=limit, offset=offset)
    return (
        [
            ReflectionResponse(
                id=r.id,
                user_id=r.user_id,
                title=r.title,
                body=r.body,
                mood=r.mood,
                is_private=r.is_private,
                date=r.date,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in reflections
        ],
        total,
    )


def get_reflection(db: Session, reflection_id: int, user_id: int) -> ReflectionResponse:
    reflection = repo.get_reflection_by_id(db, reflection_id, user_id)
    if not reflection:
        raise ReflectionNotFoundException("Reflection not found")
    return ReflectionResponse(
        id=reflection.id,
        user_id=reflection.user_id,
        title=reflection.title,
        body=reflection.body,
        mood=reflection.mood,
        is_private=reflection.is_private,
        date=reflection.date,
        created_at=reflection.created_at,
        updated_at=reflection.updated_at,
    )


def create_reflection(
    db: Session, user_id: int, payload: ReflectionCreate
) -> ReflectionResponse:
    request_id = payload.request_id
    if request_id:
        existing = repo.get_reflection_by_request_id(db, user_id, request_id)
        if existing:
            return ReflectionResponse(
                id=existing.id,
                user_id=existing.user_id,
                title=existing.title,
                body=existing.body,
                mood=existing.mood,
                is_private=existing.is_private,
                date=existing.date,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

    data = payload.model_dump(exclude_unset=True)
    if data.get("date") is None:
        data["date"] = _utcnow()

    reflection = repo.create_reflection(db, user_id, data)
    db.commit()
    db.refresh(reflection)

    return ReflectionResponse(
        id=reflection.id,
        user_id=reflection.user_id,
        title=reflection.title,
        body=reflection.body,
        mood=reflection.mood,
        is_private=reflection.is_private,
        date=reflection.date,
        created_at=reflection.created_at,
        updated_at=reflection.updated_at,
    )


def update_reflection(
    db: Session, reflection_id: int, user_id: int, payload: ReflectionUpdate
) -> ReflectionResponse:
    reflection = repo.get_reflection_by_id(db, reflection_id, user_id)
    if not reflection:
        raise ReflectionNotFoundException("Reflection not found")

    data = payload.model_dump(exclude_unset=True)
    reflection = repo.update_reflection(db, reflection, data)
    db.commit()
    db.refresh(reflection)

    return ReflectionResponse(
        id=reflection.id,
        user_id=reflection.user_id,
        title=reflection.title,
        body=reflection.body,
        mood=reflection.mood,
        is_private=reflection.is_private,
        date=reflection.date,
        created_at=reflection.created_at,
        updated_at=reflection.updated_at,
    )


def delete_reflection(db: Session, reflection_id: int, user_id: int) -> None:
    reflection = repo.get_reflection_by_id(db, reflection_id, user_id)
    if not reflection:
        raise ReflectionNotFoundException("Reflection not found")
    repo.soft_delete_reflection(db, reflection)
    db.commit()


# ---------------------------------------------------------------------------
# Adhkar Progress
# ---------------------------------------------------------------------------


def increment_adhkar_progress(
    db: Session, user_id: int, adhkar_id: int
) -> AdhkarProgressResponse:
    progress = repo.increment_adhkar_progress(db, user_id, adhkar_id)
    db.commit()
    db.refresh(progress)

    return AdhkarProgressResponse(
        id=progress.id,
        adhkar_id=progress.adhkar_id,
        count=progress.count,
        updated_at=progress.updated_at,
    )


def get_adhkar_progress(
    db: Session, user_id: int, adhkar_id: int
) -> AdhkarProgressResponse:
    progress = repo.get_adhkar_progress(db, user_id, adhkar_id)
    if not progress:
        raise ProgressNotFoundException("No progress recorded for this adhkar")
    return AdhkarProgressResponse(
        id=progress.id,
        adhkar_id=progress.adhkar_id,
        count=progress.count,
        updated_at=progress.updated_at,
    )


def list_adhkar_progress(db: Session, user_id: int) -> list[AdhkarProgressResponse]:
    progresses = repo.get_user_adhkar_progress(db, user_id)
    return [
        AdhkarProgressResponse(
            id=p.id,
            adhkar_id=p.adhkar_id,
            count=p.count,
            updated_at=p.updated_at,
        )
        for p in progresses
    ]


# ---------------------------------------------------------------------------
# Adhkar Favorites
# ---------------------------------------------------------------------------


def favorite_adhkar(
    db: Session, user_id: int, adhkar_id: int
) -> AdhkarFavoriteResponse:
    existing = repo.get_adhkar_favorite(db, user_id, adhkar_id)
    if existing:
        raise FavoriteConflictException("Already favorited")

    favorite = repo.add_adhkar_favorite(db, user_id, adhkar_id)
    db.commit()
    db.refresh(favorite)

    return AdhkarFavoriteResponse(
        id=favorite.id,
        adhkar_id=favorite.adhkar_id,
        created_at=favorite.created_at,
    )


def unfavorite_adhkar(db: Session, user_id: int, adhkar_id: int) -> None:
    favorite = repo.get_adhkar_favorite(db, user_id, adhkar_id)
    if not favorite:
        raise FavoriteNotFoundException("Favorite not found")
    repo.remove_adhkar_favorite(db, user_id, adhkar_id)
    db.commit()


def list_adhkar_favorites(db: Session, user_id: int) -> list[AdhkarFavoriteResponse]:
    favorites = repo.list_adhkar_favorites(db, user_id)
    return [
        AdhkarFavoriteResponse(
            id=f.id,
            adhkar_id=f.adhkar_id,
            created_at=f.created_at,
        )
        for f in favorites
    ]


# ---------------------------------------------------------------------------
# Reading Progress
# ---------------------------------------------------------------------------


def save_reading_progress(
    db: Session, user_id: int, book_id: int, chapter_number: int
) -> ReadingProgressResponse:
    progress = repo.upsert_reading_progress(db, user_id, book_id, chapter_number)
    db.commit()
    db.refresh(progress)
    return ReadingProgressResponse(
        book_id=progress.book_id,
        chapter_number=progress.chapter_number,
        last_read_at=progress.last_read_at,
    )


def get_last_reading(db: Session, user_id: int) -> ReadingProgressResponse | None:
    progress = repo.get_last_reading_progress(db, user_id)
    if not progress:
        return None
    return ReadingProgressResponse(
        book_id=progress.book_id,
        chapter_number=progress.chapter_number,
        last_read_at=progress.last_read_at,
    )


# ---------------------------------------------------------------------------
# Quran Progress
# ---------------------------------------------------------------------------


def save_quran_progress(
    db: Session, user_id: int, payload: QuranProgressPayload
) -> QuranProgressResponse:
    progress = repo.upsert_quran_progress(
        db,
        user_id,
        payload.surah_id,
        payload.verse_key,
        payload.page,
    )
    db.commit()
    db.refresh(progress)
    return QuranProgressResponse(
        surah_id=progress.surah_id,
        verse_key=progress.verse_key,
        page=progress.page,
        last_read_at=progress.last_read_at,
    )


def get_quran_progress(db: Session, user_id: int) -> QuranProgressResponse | None:
    progress = repo.get_quran_progress(db, user_id)
    if not progress:
        return None
    return QuranProgressResponse(
        surah_id=progress.surah_id,
        verse_key=progress.verse_key,
        page=progress.page,
        last_read_at=progress.last_read_at,
    )


def get_prayer_completions(
    db: Session, user_id: int, local_date: date
) -> PrayerCompletionState:
    rows = repo.list_prayer_completions(db, user_id, local_date)
    return PrayerCompletionState(
        local_date=local_date,
        completed_prayers=[row.prayer_name for row in rows],
    )


def set_prayer_completion(
    db: Session, user_id: int, payload: PrayerCompletionUpdate
) -> PrayerCompletionState:
    repo.set_prayer_completion(
        db,
        user_id,
        payload.local_date,
        payload.prayer_name,
        payload.completed,
    )
    db.commit()
    return get_prayer_completions(db, user_id, payload.local_date)


def list_history(
    db: Session, user_id: int, *, limit: int = 100, offset: int = 0
) -> JourneyHistoryPage:
    """Build a chronological history page without loading every event row.

    Each source contributes a narrow projection to one SQL ``UNION ALL``. The
    database performs the global ordering, count, offset and limit; Python
    only hydrates the requested page into the public response model.
    """

    nullable_string = literal(None, type_=String())
    nullable_text = literal(None, type_=Text())
    nullable_int = literal(None, type_=Integer())

    def event_projection(
        source: str,
        source_id,
        kind: str,
        title,
        description,
        occurred_at,
        reference_id,
        value_1=nullable_string,
        value_2=nullable_string,
        value_int_1=nullable_int,
        value_int_2=nullable_int,
        value_bool=literal(None),
        extra_json=nullable_text,
    ):
        return select(
            literal(source, type_=String()).label("source"),
            cast(source_id, Integer).label("source_id"),
            literal(kind, type_=String()).label("kind"),
            title.label("title"),
            description.label("description"),
            occurred_at.label("occurred_at"),
            cast(reference_id, Integer).label("reference_id"),
            value_1.label("value_1"),
            value_2.label("value_2"),
            value_int_1.label("value_int_1"),
            value_int_2.label("value_int_2"),
            value_bool.label("value_bool"),
            extra_json.label("extra_json"),
        )

    source_queries = [
        event_projection(
            "reflection",
            JourneyReflection.id,
            "reflection",
            cast(JourneyReflection.title, String()),
            cast(JourneyReflection.body, Text()),
            JourneyReflection.date,
            JourneyReflection.id,
            cast(JourneyReflection.mood, String()),
            value_bool=JourneyReflection.is_private,
        ).where(
            JourneyReflection.user_id == user_id,
            JourneyReflection.deleted_at.is_(None),
        ),
        event_projection(
            "activity",
            ActivityCompletion.id,
            "activity",
            nullable_string,
            ActivityCompletion.note,
            ActivityCompletion.completed_at,
            ActivityCompletion.id,
            cast(ActivityCompletion.activity_type, String()),
            cast(ActivityCompletion.context, String()),
        ).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.deleted_at.is_(None),
        ),
        event_projection(
            "sadaqah",
            SadaqahLog.id,
            "sadaqah",
            cast(SadaqahAct.title, String()),
            SadaqahLog.note,
            SadaqahLog.created_at,
            SadaqahLog.id,
            value_int_1=SadaqahLog.stars_earned,
        ).join(SadaqahAct, SadaqahAct.id == SadaqahLog.act_id).where(
            SadaqahLog.user_id == user_id
        ),
        event_projection(
            "prayer",
            JourneyPrayerCompletion.id,
            "prayer",
            nullable_string,
            nullable_text,
            JourneyPrayerCompletion.completed_at,
            JourneyPrayerCompletion.id,
            cast(JourneyPrayerCompletion.prayer_name, String()),
            cast(JourneyPrayerCompletion.local_date, String()),
        ).where(JourneyPrayerCompletion.user_id == user_id),
        event_projection(
            "adhkar",
            JourneyAdhkarProgress.id,
            "adhkar",
            nullable_string,
            nullable_text,
            JourneyAdhkarProgress.updated_at,
            JourneyAdhkarProgress.adhkar_id,
            value_int_1=JourneyAdhkarProgress.adhkar_id,
            value_int_2=JourneyAdhkarProgress.count,
        ).where(JourneyAdhkarProgress.user_id == user_id),
        event_projection(
            "quran",
            JourneyQuranProgress.id,
            "quran",
            nullable_string,
            nullable_text,
            JourneyQuranProgress.last_read_at,
            JourneyQuranProgress.id,
            cast(JourneyQuranProgress.verse_key, String()),
            value_int_1=JourneyQuranProgress.page,
            value_int_2=JourneyQuranProgress.surah_id,
        ).where(JourneyQuranProgress.user_id == user_id),
        event_projection(
            "book",
            JourneyReadingProgress.id,
            "book",
            nullable_string,
            nullable_text,
            JourneyReadingProgress.last_read_at,
            JourneyReadingProgress.book_id,
            value_int_1=JourneyReadingProgress.book_id,
            value_int_2=JourneyReadingProgress.chapter_number,
        ).where(JourneyReadingProgress.user_id == user_id),
        event_projection(
            "goal",
            UserGoal.id,
            "goal",
            cast(UserGoal.title, String()),
            nullable_text,
            func.coalesce(UserGoal.completed_at, UserGoal.created_at),
            UserGoal.id,
            cast(UserGoal.status, String()),
            value_int_1=UserGoal.acts_done,
            value_int_2=UserGoal.acts_target,
        ).where(UserGoal.user_id == user_id, UserGoal.deleted_at.is_(None)),
        event_projection(
            "family",
            FamilyActivity.id,
            "family",
            nullable_string,
            nullable_text,
            FamilyActivity.created_at,
            FamilyActivity.id,
            cast(FamilyActivity.event_type, String()),
            value_int_1=FamilyActivity.family_id,
            extra_json=cast(FamilyActivity.extra, Text()),
        ).where(FamilyActivity.actor_id == user_id),
    ]

    history_rows = union_all(*source_queries).subquery("journey_history")
    total = int(
        db.scalar(select(func.count()).select_from(history_rows)) or 0
    )
    rows = db.execute(
        select(history_rows)
        .order_by(
            history_rows.c.occurred_at.desc(),
            history_rows.c.source_id.desc(),
            history_rows.c.source.asc(),
        )
        .offset(offset)
        .limit(limit)
    ).mappings().all()

    events: list[JourneyHistoryItem] = []
    for row in rows:
        source = row["source"]
        value_1 = row["value_1"]
        value_2 = row["value_2"]
        value_int_1 = row["value_int_1"]
        value_int_2 = row["value_int_2"]
        title = row["title"]
        description = row["description"]
        metadata: dict[str, object] = {}

        if source == "reflection":
            title = title or "Reflection"
            metadata = {"mood": value_1, "private": row["value_bool"]}
        elif source == "activity":
            activity_value = _stored_enum_value(value_1)
            context_value = _stored_enum_value(value_2)
            activity = activity_value.replace("_", " ")
            title = f"Completed {activity}"
            metadata = {"activity_type": activity_value, "context": context_value}
        elif source == "sadaqah":
            title = title or "Sadaqah recorded"
            metadata = {"stars": value_int_1}
        elif source == "prayer":
            title = f"{str(value_1 or 'Prayer').title()} completed"
            metadata = {"local_date": value_2}
        elif source == "adhkar":
            title = "Adhkar progress updated"
            description = f"Count: {value_int_2}"
            metadata = {"count": value_int_2}
        elif source == "quran":
            title = "Quran reading progress saved"
            description = f"Page {value_int_1}, verse {value_1}"
            metadata = {"page": value_int_1, "surah_id": value_int_2}
        elif source == "book":
            title = "Book reading progress saved"
            description = f"Chapter {value_int_2}"
            metadata = {"chapter": value_int_2}
        elif source == "goal":
            status = str(value_1 or "active").lower()
            title = (
                f"Completed goal: {title}"
                if status == "completed"
                else f"Goal {status}: {title}"
            )
            description = f"{value_int_1} of {value_int_2} actions"
            metadata = {"status": status}
        elif source == "family":
            event_type = _stored_enum_value(
                value_1,
                {
                    "FAMILY_CREATED": "family.created",
                    "MEMBER_JOINED": "member.joined",
                    "MEMBER_LEFT": "member.left",
                    "MEMBER_ROLE_CHANGED": "member.role_changed",
                    "GOAL_CREATED": "goal.created",
                    "GOAL_COMPLETED": "goal.completed",
                    "PRAYER_REQUEST_CREATED": "prayer_request.created",
                    "PRAYER_REQUEST_ANSWERED": "prayer_request.answered",
                    "REFLECTION_SHARED": "reflection.shared",
                    "INVITATION_ACCEPTED": "invitation.accepted",
                    "INVITATION_DECLINED": "invitation.declined",
                    "ACT_ADDED": "act.added",
                },
            )
            title = event_type.replace(".", " ").replace("_", " ").title()
            metadata = {
                "family_id": value_int_1,
                "event_type": event_type,
            }
            if row["extra_json"]:
                import json

                try:
                    extra = json.loads(row["extra_json"])
                    if isinstance(extra, dict):
                        metadata.update(extra)
                except (TypeError, json.JSONDecodeError):
                    pass

        events.append(
            JourneyHistoryItem(
                id=f"{source}:{row['source_id']}",
                kind=row["kind"],
                title=title or source.title(),
                description=description,
                occurred_at=row["occurred_at"],
                reference_id=row["reference_id"],
                metadata=metadata,
            )
        )

    return JourneyHistoryPage(data=events, total=total, limit=limit, offset=offset)
