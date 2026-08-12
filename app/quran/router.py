from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope
from app.db.deps import get_db
from app.quran import service
from app.quran.schemas import QuranBookmarkCreate
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter(prefix="/quran", tags=["quran"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/surahs", response_model=Envelope)
def list_surahs(db: DbDep):
    return Envelope(data=service.list_surahs(db))


@router.get("/surahs/{surah_id}/ayahs", response_model=Envelope)
def get_surah_ayahs(surah_id: int, db: DbDep):
    if surah_id < 1 or surah_id > 114:
        raise HTTPException(status_code=404, detail="Surah not found")
    return Envelope(data=service.get_surah_ayahs(db, surah_id))


@router.get("/pages/{page_number}", response_model=Envelope)
def get_page(page_number: int, db: DbDep):
    if page_number < 1 or page_number > 604:
        raise HTTPException(status_code=404, detail="Mushaf page not found")
    return Envelope(data=service.get_page(db, page_number))


@router.get("/juz/{juz_number}", response_model=Envelope)
def get_juz(juz_number: int, db: DbDep):
    if juz_number < 1 or juz_number > 30:
        raise HTTPException(status_code=404, detail="Juz not found")
    return Envelope(data=service.get_juz(db, juz_number))


@router.get("/hizb/{hizb_number}", response_model=Envelope)
def get_hizb(hizb_number: int, db: DbDep):
    if hizb_number < 1 or hizb_number > 60:
        raise HTTPException(status_code=404, detail="Hizb not found")
    return Envelope(data=service.get_hizb(db, hizb_number))


@router.get("/search", response_model=Envelope)
def search(
    db: DbDep,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(20, ge=1, le=50),
):
    return Envelope(data=service.search(db, q, limit))


@router.get("/bookmarks", response_model=Envelope)
def list_bookmarks(db: DbDep, current_user: CurrentUser):
    return Envelope(data=service.list_bookmarks(db, current_user.id))


@router.post("/bookmarks", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: QuranBookmarkCreate, db: DbDep, current_user: CurrentUser):
    if payload.verse_key is None and payload.page_number is None:
        raise HTTPException(status_code=400, detail="Bookmark requires an ayah or page")
    bookmark = service.create_bookmark(
        db,
        user_id=current_user.id,
        verse_key=payload.verse_key,
        page_number=payload.page_number,
    )
    return Envelope(data=bookmark, message="Quran bookmark saved")


@router.delete("/bookmarks/{bookmark_id}", response_model=Envelope)
def delete_bookmark(bookmark_id: int, db: DbDep, current_user: CurrentUser):
    deleted = service.delete_bookmark(
        db, user_id=current_user.id, bookmark_id=bookmark_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return Envelope(data={"deleted": True}, message="Quran bookmark removed")
