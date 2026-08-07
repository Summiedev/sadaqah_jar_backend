"""Journey domain repository layer."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.journey.models import (
    JourneyReflection,
    JourneyAdhkarProgress,
    JourneyAdhkarFavorite,
    JourneyQuranProgress,
    JourneyReadingProgress,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


def list_reflections(
    db: Session, user_id: int, limit: int = 50, offset: int = 0
) -> tuple[Sequence[JourneyReflection], int]:
    total = (
        db.scalar(
            select(func.count(JourneyReflection.id)).where(
                JourneyReflection.user_id == user_id,
                JourneyReflection.deleted_at.is_(None),
            )
        )
        or 0
    )

    rows = db.scalars(
        select(JourneyReflection)
        .where(
            JourneyReflection.user_id == user_id,
            JourneyReflection.deleted_at.is_(None),
        )
        .order_by(JourneyReflection.date.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def get_reflection_by_id(
    db: Session, reflection_id: int, user_id: int
) -> JourneyReflection | None:
    return db.scalar(
        select(JourneyReflection).where(
            JourneyReflection.id == reflection_id,
            JourneyReflection.user_id == user_id,
            JourneyReflection.deleted_at.is_(None),
        )
    )


def create_reflection(db: Session, user_id: int, payload: dict) -> JourneyReflection:
    reflection = JourneyReflection(
        user_id=user_id,
        title=payload["title"],
        body=payload["body"],
        mood=payload["mood"],
        is_private=payload.get("is_private", False),
        date=payload.get("date") or _utcnow(),
        request_id=payload.get("request_id"),
    )
    db.add(reflection)
    db.flush()
    return reflection


def get_reflection_by_request_id(
    db: Session, user_id: int, request_id: str
) -> JourneyReflection | None:
    return db.scalar(
        select(JourneyReflection).where(
            JourneyReflection.user_id == user_id,
            JourneyReflection.request_id == request_id,
            JourneyReflection.deleted_at.is_(None),
        )
    )


# ---------------------------------------------------------------------------
# Adhkar Progress
# ---------------------------------------------------------------------------


def get_adhkar_progress(
    db: Session, user_id: int, adhkar_id: int
) -> JourneyAdhkarProgress | None:
    return db.scalar(
        select(JourneyAdhkarProgress).where(
            JourneyAdhkarProgress.user_id == user_id,
            JourneyAdhkarProgress.adhkar_id == adhkar_id,
        )
    )


def get_user_adhkar_progress(
    db: Session, user_id: int
) -> Sequence[JourneyAdhkarProgress]:
    return db.scalars(
        select(JourneyAdhkarProgress).where(JourneyAdhkarProgress.user_id == user_id)
    ).all()


def increment_adhkar_progress(
    db: Session, user_id: int, adhkar_id: int
) -> JourneyAdhkarProgress:
    progress = get_adhkar_progress(db, user_id, adhkar_id)
    if progress is None:
        progress = JourneyAdhkarProgress(user_id=user_id, adhkar_id=adhkar_id, count=1)
        db.add(progress)
    else:
        progress.count += 1
    db.flush()
    return progress


# ---------------------------------------------------------------------------
# Adhkar Favorites
# ---------------------------------------------------------------------------


def get_adhkar_favorite(
    db: Session, user_id: int, adhkar_id: int
) -> JourneyAdhkarFavorite | None:
    return db.scalar(
        select(JourneyAdhkarFavorite).where(
            JourneyAdhkarFavorite.user_id == user_id,
            JourneyAdhkarFavorite.adhkar_id == adhkar_id,
        )
    )


def list_adhkar_favorites(db: Session, user_id: int) -> Sequence[JourneyAdhkarFavorite]:
    return db.scalars(
        select(JourneyAdhkarFavorite)
        .where(JourneyAdhkarFavorite.user_id == user_id)
        .order_by(JourneyAdhkarFavorite.created_at.desc())
    ).all()


def add_adhkar_favorite(
    db: Session, user_id: int, adhkar_id: int
) -> JourneyAdhkarFavorite:
    favorite = JourneyAdhkarFavorite(user_id=user_id, adhkar_id=adhkar_id)
    db.add(favorite)
    db.flush()
    return favorite


def remove_adhkar_favorite(db: Session, user_id: int, adhkar_id: int) -> None:
    favorite = get_adhkar_favorite(db, user_id, adhkar_id)
    if favorite is not None:
        db.delete(favorite)
        db.flush()


# ---------------------------------------------------------------------------
# Reading Progress
# ---------------------------------------------------------------------------


def upsert_reading_progress(
    db: Session, user_id: int, book_id: int, chapter_number: int
) -> JourneyReadingProgress:
    progress = db.scalar(
        select(JourneyReadingProgress).where(
            JourneyReadingProgress.user_id == user_id,
            JourneyReadingProgress.book_id == book_id,
        )
    )
    now = _utcnow()
    if progress is None:
        progress = JourneyReadingProgress(
            user_id=user_id,
            book_id=book_id,
            chapter_number=chapter_number,
            last_read_at=now,
        )
        db.add(progress)
    else:
        progress.chapter_number = chapter_number
        progress.last_read_at = now
    db.flush()
    return progress


def get_last_reading_progress(
    db: Session, user_id: int
) -> JourneyReadingProgress | None:
    return db.scalar(
        select(JourneyReadingProgress)
        .where(JourneyReadingProgress.user_id == user_id)
        .order_by(JourneyReadingProgress.last_read_at.desc())
        .limit(1)
    )


# ---------------------------------------------------------------------------
# Quran Progress
# ---------------------------------------------------------------------------


def upsert_quran_progress(
    db: Session, user_id: int, surah_id: int, verse_key: str, page: int
) -> JourneyQuranProgress:
    progress = db.scalar(
        select(JourneyQuranProgress).where(JourneyQuranProgress.user_id == user_id)
    )
    now = _utcnow()
    if progress is None:
        progress = JourneyQuranProgress(
            user_id=user_id,
            surah_id=surah_id,
            verse_key=verse_key,
            page=page,
            last_read_at=now,
        )
        db.add(progress)
    else:
        progress.surah_id = surah_id
        progress.verse_key = verse_key
        progress.page = page
        progress.last_read_at = now
    db.flush()
    return progress


def get_quran_progress(db: Session, user_id: int) -> JourneyQuranProgress | None:
    return db.scalar(
        select(JourneyQuranProgress)
        .where(JourneyQuranProgress.user_id == user_id)
        .limit(1)
    )
