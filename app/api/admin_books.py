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
from app.books import repository as repo
from app.books.schemas import (
    BookChapterCreate,
    BookChapterUpdate,
    BookCreate,
    BookUpdate,
)
from app.services.storage import (
    upload_file,
    delete_file,
    get_presigned_url,
    _get_bucket,
)
from app.services.file_validation import (
    EPUB_MIME,
    JPEG_MIME,
    PDF_MIME,
    PNG_MIME,
    validate_file_content,
)

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
        "file_format": book.file_format,
        "category": book.category,
        "language": book.language,
        "published": book.published,
        "sort_order": book.sort_order,
        "page_count": getattr(book, "page_count", 0),
    }


def _object_url(bucket: str, key: str) -> str:
    return f"{os.getenv('S3_ENDPOINT_URL', 'http://127.0.0.1:9000').rstrip('/')}/{bucket}/{key}"


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


def _detail_payload(book_detail) -> dict:
    payload = book_detail.model_dump()
    if payload.get("file_url"):
        payload["file_url"] = _signed_url(payload.get("file_url"))
    for page in payload.get("pages", []) or []:
        page["image_url"] = _signed_url(page.get("image_url")) or ""
    return payload


def _has_readable_content(book_detail) -> bool:
    return bool(
        book_detail.file_url
        or book_detail.page_count > 0
        or book_detail.chapter_count > 0
    )


def _extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def _serialize_chapter(chapter) -> dict:
    return {
        "id": chapter.id,
        "book_id": chapter.book_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "content": chapter.content,
        "reading_time_minutes": chapter.reading_time_minutes or 0,
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


@router.get("/{book_id}")
def get_admin_book(
    book_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    book = service.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return _detail_payload(book)


@router.post("/", status_code=201)
def create_admin_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if payload.published and not payload.file_url:
        raise HTTPException(
            status_code=400,
            detail="Upload readable content before publishing this book",
        )
    book = service.create_book(db, payload)
    db.commit()
    return _serialize(book)


@router.post("/{book_id}/file")
async def upload_book_file(
    book_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = service.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    suffix = _extension(file.filename)
    allowed = {".pdf", ".epub"}
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Upload a PDF or EPUB file")
    content = await file.read()
    content_type = validate_file_content(
        content,
        allowed_mimes={PDF_MIME, EPUB_MIME},
        max_size_bytes=100 * 1024 * 1024,
        label="Book file",
    )

    bucket = _get_bucket()
    key = f"books/{book_id}/{uuid4().hex}{suffix}"

    upload_file(
        bucket=bucket,
        key=key,
        data=io.BytesIO(content),
        content_type=content_type,
    )

    # Remove old file if it exists
    if book.file_url:
        old_key = (
            book.file_url.split(f"/{bucket}/")[-1]
            if f"/{bucket}/" in book.file_url
            else None
        )
        if old_key:
            try:
                delete_file(bucket=bucket, key=old_key)
            except HTTPException:
                pass
    for old_page in repo.list_pages(db, book_id):
        old_key = _key_from_url(old_page.image_url, bucket)
        if old_key:
            try:
                delete_file(bucket=bucket, key=old_key)
            except HTTPException:
                pass

    object_url = _object_url(bucket, key)
    repo.replace_pages(db, book_id, [])
    updated = service.update_book(
        db,
        book_id,
        BookUpdate(
            file_url=object_url,
            file_type=content_type,
            file_format=suffix.lstrip("."),
        ),
    )
    db.commit()
    return _serialize(updated)


@router.post("/{book_id}/cover")
async def upload_book_cover(
    book_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = service.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    suffix = _extension(file.filename)
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="Upload a JPG or PNG cover image")
    content = await file.read()
    content_type = validate_file_content(
        content,
        allowed_mimes={JPEG_MIME, PNG_MIME},
        max_size_bytes=10 * 1024 * 1024,
        label="Cover image",
    )

    bucket = _get_bucket()
    key = f"books/{book_id}/cover/{uuid4().hex}{suffix}"
    upload_file(
        bucket=bucket,
        key=key,
        data=io.BytesIO(content),
        content_type=content_type,
        max_size_bytes=10 * 1024 * 1024,
    )
    old_key = _key_from_url(book.cover_url, bucket)
    if old_key:
        try:
            delete_file(bucket=bucket, key=old_key)
        except HTTPException:
            pass
    updated = service.update_book(
        db, book_id, BookUpdate(cover_url=_object_url(bucket, key))
    )
    db.commit()
    return _serialize(updated)


@router.post("/{book_id}/pages")
async def upload_book_pages(
    book_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = service.get_book_detail(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one page image")

    bucket = _get_bucket()
    pages = []
    for index, file in enumerate(files, start=1):
        suffix = _extension(file.filename)
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(
                status_code=400, detail="Page images must be JPG or PNG"
            )
        content = await file.read()
        content_type = validate_file_content(
            content,
            allowed_mimes={JPEG_MIME, PNG_MIME},
            max_size_bytes=12 * 1024 * 1024,
            label="Page image",
        )
        key = f"books/{book_id}/pages/{index:04d}-{uuid4().hex}{suffix}"
        upload_file(
            bucket=bucket,
            key=key,
            data=io.BytesIO(content),
            content_type=content_type,
            max_size_bytes=12 * 1024 * 1024,
        )
        pages.append(
            {
                "page_number": index,
                "image_url": _object_url(bucket, key),
                "image_type": content_type,
            }
        )

    for old_page in repo.list_pages(db, book_id):
        old_key = _key_from_url(old_page.image_url, bucket)
        if old_key:
            try:
                delete_file(bucket=bucket, key=old_key)
            except HTTPException:
                pass
    old_file_key = _key_from_url(book.file_url, bucket)
    if old_file_key:
        try:
            delete_file(bucket=bucket, key=old_file_key)
        except HTTPException:
            pass
    repo.replace_pages(db, book_id, pages)
    book_model = repo.get_book(db, book_id)
    if book_model:
        book_model.file_url = None
        book_model.file_type = "image-pages"
        book_model.file_format = "images"
        db.add(book_model)
        db.flush()
    updated = service.get_book_detail(db, book_id)
    db.commit()
    return _serialize(updated)


@router.get("/{book_id}/file/download")
def download_book_file(
    book_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    book = service.get_book_detail(db, book_id)
    if not book or not book.file_url:
        raise HTTPException(
            status_code=404, detail="No reading file has been uploaded for this book"
        )

    # Extract key from URL
    bucket = _get_bucket()
    key = (
        book.file_url.split(f"/{bucket}/")[-1]
        if f"/{bucket}/" in book.file_url
        else None
    )
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
    if payload.published is True:
        detail = service.get_book_detail(db, book_id)
        if detail and not _has_readable_content(detail):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Upload readable content before publishing this book",
            )
    db.commit()
    return _serialize(book)


@router.delete("/{book_id}")
def delete_admin_book(
    book_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    book = repo.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Remove object-storage files as part of the admin delete flow. The book
    # row is soft-deleted for referential safety, but leaving its PDF/EPUB,
    # cover, or page images behind would leak storage and orphan private data.
    try:
        bucket = _get_bucket()
    except HTTPException:
        bucket = None
    if bucket:
        urls = [book.file_url, book.cover_url]
        urls.extend(page.image_url for page in repo.list_pages(db, book_id))
        for raw_url in urls:
            key = _key_from_url(raw_url, bucket)
            if key:
                try:
                    delete_file(bucket=bucket, key=key)
                except HTTPException:
                    # The database delete remains authoritative if an old
                    # object has already been removed from storage.
                    pass
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
