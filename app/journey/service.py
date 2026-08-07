"""Journey domain service layer."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.journey import repository as repo
from app.journey.exceptions import (
    FavoriteConflictException,
    FavoriteNotFoundException,
    ProgressNotFoundException,
    ReflectionNotFoundException,
)
from app.journey.schemas import (
    ReadingProgressResponse,
    ReflectionCreate,
    ReflectionResponse,
    AdhkarProgressResponse,
    AdhkarFavoriteResponse,
)


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
