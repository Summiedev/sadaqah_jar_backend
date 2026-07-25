"""Books domain router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.books import service
from app.books import repository as repo
from app.books.schemas import BookChapterCreate, BookChapterUpdate, BookCreate, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("/", response_model=Envelope)
def list_books(db: DbDep, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    result = service.list_books(db, offset=offset, limit=limit, published_only=True)
    return Envelope(data=result.data, meta=Meta(total=result.total, limit=result.limit, offset=result.offset))


@router.get("/{book_id}", response_model=Envelope)
def get_book(book_id: int, db: DbDep):
    book = service.get_book_detail(db, book_id)
    if not book:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Book not found")
    return Envelope(data=book)


@router.get("/{book_id}/chapters", response_model=Envelope)
def list_chapters(book_id: int, db: DbDep):
    chapters = service.list_chapters(db, book_id)
    return Envelope(data=chapters)


@router.get("/{book_id}/chapters/{chapter_number}", response_model=Envelope)
def get_chapter(book_id: int, chapter_number: int, db: DbDep):
    from fastapi import HTTPException
    chapter = repo.get_chapter_by_number(db, book_id, chapter_number)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    from app.books.schemas import BookChapterRead
    return Envelope(data=BookChapterRead(
        id=chapter.id,
        book_id=chapter.book_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        content=chapter.content,
        reading_time_minutes=chapter.reading_time_minutes,
    ))
