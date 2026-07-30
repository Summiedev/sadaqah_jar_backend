from pathlib import Path
from uuid import uuid4
import io
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.books import service
from app.books.schemas import BookChapterCreate, BookChapterUpdate, BookCreate, BookUpdate
from app.services.storage import upload_file, delete_file, get_presigned_url, _get_bucket

router = APIRouter(prefix="/admin/books", tags=["Admin Books"])


def _serialize(book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "cover_url": book.cover_url,
        "file_url": book.file_url,
        "file_type": book.file_type,
        "category": book.category,
        "language": book.language,
        "published": book.published,
        "sort_order": book.sort_order,
    }


def _serialize_chapter(chapter) -> dict:
    return {
        "id": chapter.id,
        "book_id": chapter.book_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "content": chapter.content,
        "reading_time_minutes": chapter.reading_time_minutes,
    }


@router.get("/")
def list_admin_books(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    result = service.list_books(db, offset=offset, limit=limit, published_only=False)
    return {
        "total": result.total,
        "limit": result.limit,
        "offset": result.offset,
        "data": [_serialize(b) for b in result.data],
    }


@router.post("/", status_code=201)
def create_admin_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = service.create_book(db, payload)
    db.commit()
    return _serialize(book)


@router.post("/{book_id}/file")
async def upload_book_file(book_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin=Depends(require_admin)):
    book = service.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".epub", ".txt", ".md"}
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Upload a PDF, EPUB, TXT, or Markdown file")
    content = await file.read()
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Choose a file between 1 byte and 25 MB")

    bucket = _get_bucket()
    key = f"books/{book_id}/{uuid4().hex}{suffix}"

    upload_file(
        bucket=bucket,
        key=key,
        data=io.BytesIO(content),
        content_type=file.content_type or f"application/{suffix.lstrip('.')}",
    )

    # Remove old file if it exists
    if book.file_url:
        old_key = book.file_url.split(f"/{bucket}/")[-1] if f"/{bucket}/" in book.file_url else None
        if old_key:
            try:
                delete_file(bucket=bucket, key=old_key)
            except HTTPException:
                pass

    object_url = f"{os.getenv('S3_ENDPOINT_URL', 'http://127.0.0.1:9000').rstrip('/')}/{bucket}/{key}"
    updated = service.update_book(db, book_id, BookUpdate(file_url=object_url, file_type=file.content_type or suffix.lstrip(".")))
    db.commit()
    return _serialize(updated)


@router.get("/{book_id}/file/download")
def download_book_file(book_id: int, db: Session = Depends(get_db)):
    book = service.get_book_detail(db, book_id)
    if not book or not book.file_url:
        raise HTTPException(status_code=404, detail="No reading file has been uploaded for this book")

    # Extract key from URL
    bucket = _get_bucket()
    key = book.file_url.split(f"/{bucket}/")[-1] if f"/{bucket}/" in book.file_url else None
    if not key:
        raise HTTPException(status_code=404, detail="Invalid file URL")

    presigned_url = get_presigned_url(bucket=bucket, key=key, expires_in=3600)
    return RedirectResponse(url=presigned_url)


@router.patch("/{book_id}")
def update_admin_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = service.update_book(db, book_id, payload)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.commit()
    return _serialize(book)


@router.delete("/{book_id}")
def delete_admin_book(
    book_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    service.delete_book(db, book_id)
    db.commit()
    return {"message": "Book deleted"}


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


@router.get("/{book_id}/chapters")
def list_admin_chapters(
    book_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    chapters = service.list_chapters(db, book_id)
    return {"data": [_serialize_chapter(c) for c in chapters]}


@router.post("/{book_id}/chapters", status_code=201)
def create_admin_chapter(
    book_id: int,
    payload: BookChapterCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    chapter = service.create_chapter(db, book_id, payload)
    if not chapter:
        raise HTTPException(status_code=404, detail="Book not found")
    db.commit()
    return _serialize_chapter(chapter)


@router.patch("/{book_id}/chapters/{chapter_id}")
def update_admin_chapter(
    book_id: int,
    chapter_id: int,
    payload: BookChapterUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    chapter = service.update_chapter(db, chapter_id, payload)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    db.commit()
    return _serialize_chapter(chapter)


@router.delete("/{book_id}/chapters/{chapter_id}")
def delete_admin_chapter(
    book_id: int,
    chapter_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    service.delete_chapter(db, chapter_id)
    db.commit()
    return {"message": "Chapter deleted"}
