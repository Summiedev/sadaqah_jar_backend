from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Meta
from app.db.deps import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.books import service as book_service
from app.books.bookmark_repository import (
    create_bookmark,
    delete_bookmark,
    get_bookmark,
    list_user_bookmarks,
)
from app.books.bookmark_schemas import (
    BookmarkCreateRequest,
    BookmarkListResponse,
    BookBookmarkResponse,
)

router = APIRouter(prefix="/books", tags=["books"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/{book_id}/bookmark", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def bookmark_book(
    book_id: int,
    payload: BookmarkCreateRequest,
    db: DbDep,
    current_user: CurrentUser,
):
    """Bookmark a book (optionally at a specific chapter)."""
    existing = get_bookmark(db, current_user.id, book_id)
    if existing:
        return Envelope(
            data=BookBookmarkResponse(
                id=existing.id,
                user_id=existing.user_id,
                book_id=existing.book_id,
                chapter_number=existing.chapter_number,
                created_at=existing.created_at.isoformat(),
            ),
            message="Bookmark already exists",
        )

    bookmark = create_bookmark(
        db,
        user_id=current_user.id,
        book_id=book_id,
        chapter_number=payload.chapter_number,
    )
    db.commit()

    return Envelope(
        data=BookBookmarkResponse(
            id=bookmark.id,
            user_id=bookmark.user_id,
            book_id=bookmark.book_id,
            chapter_number=bookmark.chapter_number,
            created_at=bookmark.created_at.isoformat(),
        ),
        message="Book bookmarked",
    )


@router.delete("/{book_id}/bookmark", response_model=Envelope)
def unbookmark_book(
    book_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    """Remove a bookmark for a book."""
    deleted = delete_bookmark(db, current_user.id, book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.commit()
    return Envelope(data=None, message="Bookmark removed")


@router.get("/bookmarks", response_model=Envelope)
def list_bookmarks(
    db: DbDep,
    current_user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List the current user's book bookmarks."""
    bookmarks = list_user_bookmarks(db, current_user.id, offset=offset, limit=limit)
    total = len(bookmarks)
    return Envelope(
        data=BookmarkListResponse(
            total=total,
            data=[
                BookBookmarkResponse(
                    id=b.id,
                    user_id=b.user_id,
                    book_id=b.book_id,
                    chapter_number=b.chapter_number,
                    created_at=b.created_at.isoformat(),
                )
                for b in bookmarks
            ],
        )
    )