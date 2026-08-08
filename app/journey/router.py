"""Journey domain router.

Only user-state endpoints are exposed. Static catalogue content
(adhkar text, categories, readings) is bundled with the Flutter app
and never touches this API.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.journey import service
from app.journey.schemas import (
    QuranProgressPayload,
    ReadingProgressResponse,
    ReflectionCreate,
    ReflectionUpdate,
)

router = APIRouter(prefix="/journey", tags=["journey"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Reflections
# ---------------------------------------------------------------------------


@router.get("/reflections", response_model=Envelope)
def list_reflections(
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    reflections, total = service.list_reflections(
        db, current_user.id, limit=limit, offset=offset
    )
    return Envelope(data=reflections, meta=Meta(total=total))


@router.get("/reflections/{reflection_id}", response_model=Envelope)
def get_reflection(reflection_id: int, db: DbDep, current_user: CurrentUser):
    reflection = service.get_reflection(db, reflection_id, current_user.id)
    return Envelope(data=reflection)


@router.post(
    "/reflections", response_model=Envelope, status_code=status.HTTP_201_CREATED
)
def create_reflection(payload: ReflectionCreate, db: DbDep, current_user: CurrentUser):
    reflection = service.create_reflection(db, current_user.id, payload)
    return Envelope(data=reflection, message="Reflection saved")


@router.patch("/reflections/{reflection_id}", response_model=Envelope)
def update_reflection(
    reflection_id: int,
    payload: ReflectionUpdate,
    db: DbDep,
    current_user: CurrentUser,
):
    reflection = service.update_reflection(db, reflection_id, current_user.id, payload)
    return Envelope(data=reflection, message="Reflection updated")


# ---------------------------------------------------------------------------
# Adhkar Progress
# ---------------------------------------------------------------------------


@router.post(
    "/adhkar/{adhkar_id}/progress",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
def increment_adhkar_progress(adhkar_id: int, db: DbDep, current_user: CurrentUser):
    progress = service.increment_adhkar_progress(db, current_user.id, adhkar_id)
    return Envelope(data=progress, message="Progress updated")


@router.get("/adhkar/progress", response_model=Envelope)
def get_my_adhkar_progress(db: DbDep, current_user: CurrentUser):
    progresses = service.list_adhkar_progress(db, current_user.id)
    return Envelope(data=progresses)


@router.get("/adhkar/{adhkar_id}/progress", response_model=Envelope)
def get_adhkar_item_progress(adhkar_id: int, db: DbDep, current_user: CurrentUser):
    progress = service.get_adhkar_progress(db, current_user.id, adhkar_id)
    return Envelope(data=progress)


# ---------------------------------------------------------------------------
# Adhkar Favorites
# ---------------------------------------------------------------------------


@router.post(
    "/adhkar/{adhkar_id}/favorite",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
def favorite_adhkar(adhkar_id: int, db: DbDep, current_user: CurrentUser):
    favorite = service.favorite_adhkar(db, current_user.id, adhkar_id)
    return Envelope(data=favorite, message="Added to favorites")


@router.delete("/adhkar/{adhkar_id}/favorite", response_model=Envelope)
def unfavorite_adhkar(adhkar_id: int, db: DbDep, current_user: CurrentUser):
    service.unfavorite_adhkar(db, current_user.id, adhkar_id)
    return Envelope(message="Removed from favorites")


@router.get("/adhkar/favorites", response_model=Envelope)
def list_adhkar_favorites(db: DbDep, current_user: CurrentUser):
    favorites = service.list_adhkar_favorites(db, current_user.id)
    return Envelope(data=favorites)


# ---------------------------------------------------------------------------
# Reading Progress
# ---------------------------------------------------------------------------


@router.post(
    "/reading/progress", response_model=Envelope, status_code=status.HTTP_201_CREATED
)
def save_reading_progress(
    payload: ReadingProgressResponse,
    db: DbDep,
    current_user: CurrentUser,
):
    progress = service.save_reading_progress(
        db, current_user.id, payload.book_id, payload.chapter_number
    )
    return Envelope(data=progress, message="Progress saved")


@router.get("/reading/last", response_model=Envelope)
def get_last_reading(db: DbDep, current_user: CurrentUser):
    progress = service.get_last_reading(db, current_user.id)
    if progress is None:
        return Envelope(data=None)
    return Envelope(data=progress)


# ---------------------------------------------------------------------------
# Quran Progress
# ---------------------------------------------------------------------------


@router.post(
    "/quran/progress", response_model=Envelope, status_code=status.HTTP_201_CREATED
)
def save_quran_progress(
    payload: QuranProgressPayload,
    db: DbDep,
    current_user: CurrentUser,
):
    progress = service.save_quran_progress(db, current_user.id, payload)
    return Envelope(data=progress, message="Quran progress saved")


@router.get("/quran/progress", response_model=Envelope)
def get_quran_progress(db: DbDep, current_user: CurrentUser):
    progress = service.get_quran_progress(db, current_user.id)
    return Envelope(data=progress)
