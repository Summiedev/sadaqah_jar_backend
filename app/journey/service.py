"""Journey domain service layer."""

from datetime import date, datetime, timezone

from sqlalchemy import select
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    """Build one chronological view over the user's existing activity tables."""
    events: list[JourneyHistoryItem] = []

    reflections = db.scalars(
        select(JourneyReflection).where(
            JourneyReflection.user_id == user_id,
            JourneyReflection.deleted_at.is_(None),
        )
    ).all()
    for item in reflections:
        events.append(
            JourneyHistoryItem(
                id=f"reflection:{item.id}",
                kind="reflection",
                title=item.title or "Reflection",
                description=item.body,
                occurred_at=item.date or item.created_at,
                reference_id=item.id,
                metadata={"mood": item.mood, "private": item.is_private},
            )
        )

    completions = db.scalars(
        select(ActivityCompletion).where(
            ActivityCompletion.user_id == user_id,
            ActivityCompletion.deleted_at.is_(None),
        )
    ).all()
    for item in completions:
        activity = getattr(item.activity_type, "value", str(item.activity_type))
        events.append(
            JourneyHistoryItem(
                id=f"activity:{item.id}",
                kind="activity",
                title=f"Completed {activity.replace('_', ' ')}",
                description=item.note,
                occurred_at=item.completed_at,
                reference_id=item.id,
                metadata={
                    "activity_type": activity,
                    "context": getattr(item.context, "value", str(item.context)),
                },
            )
        )

    legacy_rows = db.execute(
        select(SadaqahLog, SadaqahAct.title)
        .join(SadaqahAct, SadaqahAct.id == SadaqahLog.act_id)
        .where(SadaqahLog.user_id == user_id)
    ).all()
    for log, act_title in legacy_rows:
        events.append(
            JourneyHistoryItem(
                id=f"sadaqah:{log.id}",
                kind="sadaqah",
                title=act_title or "Sadaqah recorded",
                description=log.note,
                occurred_at=log.created_at,
                reference_id=log.id,
                metadata={"stars": log.stars_earned},
            )
        )

    prayer_rows = db.scalars(
        select(JourneyPrayerCompletion).where(
            JourneyPrayerCompletion.user_id == user_id
        )
    ).all()
    for item in prayer_rows:
        events.append(
            JourneyHistoryItem(
                id=f"prayer:{item.id}",
                kind="prayer",
                title=f"{item.prayer_name.title()} completed",
                occurred_at=item.completed_at,
                reference_id=item.id,
                metadata={"local_date": item.local_date.isoformat()},
            )
        )

    adhkar_rows = db.scalars(
        select(JourneyAdhkarProgress).where(JourneyAdhkarProgress.user_id == user_id)
    ).all()
    for item in adhkar_rows:
        events.append(
            JourneyHistoryItem(
                id=f"adhkar:{item.id}",
                kind="adhkar",
                title="Adhkar progress updated",
                description=f"Count: {item.count}",
                occurred_at=item.updated_at,
                reference_id=item.adhkar_id,
                metadata={"count": item.count},
            )
        )

    quran = db.scalar(
        select(JourneyQuranProgress).where(JourneyQuranProgress.user_id == user_id)
    )
    if quran:
        events.append(
            JourneyHistoryItem(
                id=f"quran:{quran.id}",
                kind="quran",
                title="Quran reading progress saved",
                description=f"Page {quran.page}, verse {quran.verse_key}",
                occurred_at=quran.last_read_at,
                reference_id=quran.id,
                metadata={"page": quran.page, "surah_id": quran.surah_id},
            )
        )

    reading_rows = db.scalars(
        select(JourneyReadingProgress).where(JourneyReadingProgress.user_id == user_id)
    ).all()
    for item in reading_rows:
        events.append(
            JourneyHistoryItem(
                id=f"book:{item.id}",
                kind="book",
                title="Book reading progress saved",
                description=f"Chapter {item.chapter_number}",
                occurred_at=item.last_read_at,
                reference_id=item.book_id,
                metadata={"chapter": item.chapter_number},
            )
        )

    events.sort(key=lambda item: item.occurred_at, reverse=True)
    total = len(events)
    return JourneyHistoryPage(
        data=events[offset : offset + limit], total=total, limit=limit, offset=offset
    )
