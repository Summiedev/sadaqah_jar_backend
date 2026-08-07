from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.books.bookmark_model import BookBookmark
from app.db.session import SessionLocal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_db():
    return SessionLocal()


def create_bookmark(
    db, user_id: int, book_id: int, chapter_number: int | None = None
) -> BookBookmark:
    bookmark = BookBookmark(
        user_id=user_id, book_id=book_id, chapter_number=chapter_number
    )
    db.add(bookmark)
    db.flush()
    db.refresh(bookmark)
    return bookmark


def get_bookmark(db, user_id: int, book_id: int) -> BookBookmark | None:
    return db.scalar(
        select(BookBookmark).where(
            BookBookmark.user_id == user_id,
            BookBookmark.book_id == book_id,
        )
    )


def delete_bookmark(db, user_id: int, book_id: int) -> bool:
    bookmark = get_bookmark(db, user_id, book_id)
    if bookmark:
        db.delete(bookmark)
        db.flush()
        return True
    return False


def list_user_bookmarks(
    db, user_id: int, offset: int = 0, limit: int = 50
) -> list[BookBookmark]:
    return list(
        db.scalars(
            select(BookBookmark)
            .where(BookBookmark.user_id == user_id)
            .order_by(BookBookmark.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
