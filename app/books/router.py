"""Books domain router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.books import service
from app.books import repository as repo
from app.services.storage import get_presigned_url, _get_bucket

router = APIRouter(prefix="/books", tags=["books"])

DbDep = Annotated[Session, Depends(get_db)]


def _key_from_url(raw_url: str | None, bucket: str) -> str | None:
    if not raw_url:
        return None
    return raw_url.split(f"/{bucket}/")[-1] if f"/{bucket}/" in raw_url else None


def _signed_url(raw_url: str | None) -> str | None:
    bucket = _get_bucket()
    key = _key_from_url(raw_url, bucket)
    if not key:
        return raw_url
    return get_presigned_url(bucket=bucket, key=key, expires_in=3600)


def _public_book_payload(book, *, include_download_link: bool = True) -> dict:
    payload = book.model_dump()
    if include_download_link and payload.get("file_url"):
        payload["file_url"] = f"/books/{book.id}/file/download"
    for page in payload.get("pages", []) or []:
        page["image_url"] = _signed_url(page.get("image_url")) or ""
    return payload


@router.get("/", response_model=Envelope)
def list_books(
    db: DbDep, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    result = service.list_books(db, offset=offset, limit=limit, published_only=True)
    data = []
    for book in result.data:
        payload = book.model_dump()
        if payload.get("file_url"):
            payload["file_url"] = f"/books/{book.id}/file/download"
        data.append(payload)
    return Envelope(
        data=data,
        meta=Meta(total=result.total, limit=result.limit, offset=result.offset),
    )


@router.get("/{book_id}", response_model=Envelope)
def get_book(book_id: int, db: DbDep):
    book = service.get_book_detail(db, book_id, published_only=True)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return Envelope(data=_public_book_payload(book))


@router.get("/{book_id}/chapters", response_model=Envelope)
def list_chapters(book_id: int, db: DbDep):
    if not repo.get_book(db, book_id, published_only=True):
        raise HTTPException(status_code=404, detail="Book not found")
    chapters = service.list_chapters(db, book_id)
    return Envelope(data=chapters)


@router.get("/{book_id}/chapters/{chapter_number}", response_model=Envelope)
def get_chapter(book_id: int, chapter_number: int, db: DbDep):
    if not repo.get_book(db, book_id, published_only=True):
        raise HTTPException(status_code=404, detail="Book not found")
    chapter = repo.get_chapter_by_number(db, book_id, chapter_number)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    from app.books.schemas import BookChapterRead

    return Envelope(
        data=BookChapterRead(
            id=chapter.id,
            book_id=chapter.book_id,
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            content=chapter.content,
            reading_time_minutes=chapter.reading_time_minutes,
        )
    )


@router.get("/{book_id}/file/download")
def download_book_file(book_id: int, db: DbDep):
    book = repo.get_book(db, book_id, published_only=True)
    if not book or not book.file_url:
        raise HTTPException(status_code=404, detail="Reading file not found")
    bucket = _get_bucket()
    key = _key_from_url(book.file_url, bucket)
    if not key:
        raise HTTPException(status_code=404, detail="Invalid file URL")
    return RedirectResponse(
        url=get_presigned_url(bucket=bucket, key=key, expires_in=3600)
    )
