from datetime import datetime, timezone

from sqlalchemy import select, func

from app.books.models import Book, BookChapter
from app.db.session import SessionLocal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_db():
    return SessionLocal()


def _get_db():
    return SessionLocal()


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


def list_books(db, published_only: bool = True, offset: int = 0, limit: int = 50) -> tuple[list[Book], int]:
    query = select(Book).where(Book.deleted_at.is_(None))
    if published_only:
        query = query.where(Book.published.is_(True))
    query = query.order_by(Book.sort_order.asc(), Book.id.asc())
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.offset(offset).limit(limit)).all()
    return list(rows), total or 0


def get_book(db, book_id: int) -> Book | None:
    return db.scalar(select(Book).where(Book.id == book_id, Book.deleted_at.is_(None)))


def create_book(db, payload: dict) -> Book:
    book = Book(**payload)
    db.add(book)
    db.flush()
    db.refresh(book)
    return book


def update_book(db, book: Book, payload: dict) -> Book:
    for key, value in payload.items():
        if value is not None and hasattr(book, key):
            setattr(book, key, value)
    db.add(book)
    db.flush()
    db.refresh(book)
    return book


def delete_book(db, book_id: int) -> None:
    book = get_book(db, book_id)
    if book:
        book.deleted_at = _utcnow()
        db.add(book)


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


def get_chapter(db, chapter_id: int) -> BookChapter | None:
    return db.scalar(select(BookChapter).where(BookChapter.id == chapter_id))


def get_chapter_by_number(db, book_id: int, chapter_number: int) -> BookChapter | None:
    return db.scalar(
        select(BookChapter).where(
            BookChapter.book_id == book_id,
            BookChapter.chapter_number == chapter_number,
        )
    )


def list_chapters(db, book_id: int) -> list[BookChapter]:
    return list(
        db.scalars(
            select(BookChapter).where(BookChapter.book_id == book_id).order_by(BookChapter.chapter_number.asc())
        ).all()
    )


def create_chapter(db, payload: dict) -> BookChapter:
    chapter = BookChapter(**payload)
    db.add(chapter)
    db.flush()
    db.refresh(chapter)
    return chapter


def update_chapter(db, chapter: BookChapter, payload: dict) -> BookChapter:
    for key, value in payload.items():
        if value is not None and hasattr(chapter, key):
            setattr(chapter, key, value)
    db.add(chapter)
    db.flush()
    db.refresh(chapter)
    return chapter


def delete_chapter(db, chapter_id: int) -> None:
    chapter = get_chapter(db, chapter_id)
    if chapter:
        db.delete(chapter)
