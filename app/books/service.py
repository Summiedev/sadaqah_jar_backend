from app.books import repository as repo
from app.books.schemas import (
    BookChapterRead,
    BookChapterCreate,
    BookChapterUpdate,
    BookCreate,
    BookListResponse,
    BookRead,
    BookUpdate,
)


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


def list_books(db, offset: int = 0, limit: int = 50, published_only: bool = True) -> BookListResponse:
    rows, total = repo.list_books(db, published_only=published_only, offset=offset, limit=limit)
    data = [_serialize(db, book) for book in rows]
    return BookListResponse(total=total, limit=limit, offset=offset, data=data)


def get_book_detail(db, book_id: int) -> BookRead | None:
    book = repo.get_book(db, book_id)
    if not book:
        return None
    return _serialize_detail(db, book)


def create_book(db, payload: BookCreate) -> BookRead:
    book = repo.create_book(db, payload.model_dump(exclude_none=True))
    return _serialize(db, book)


def update_book(db, book_id: int, payload: BookUpdate) -> BookRead | None:
    book = repo.get_book(db, book_id)
    if not book:
        return None
    book = repo.update_book(db, book, payload.model_dump(exclude_none=True))
    return _serialize(db, book)


def delete_book(db, book_id: int) -> None:
    repo.delete_book(db, book_id)


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


def get_chapter(db, chapter_id: int):
    return repo.get_chapter(db, chapter_id)


def list_chapters(db, book_id: int) -> list[BookChapterRead]:
    chapters = repo.list_chapters(db, book_id)
    return [
        BookChapterRead(
            id=c.id,
            book_id=c.book_id,
            chapter_number=c.chapter_number,
            title=c.title,
            content=c.content,
            reading_time_minutes=c.reading_time_minutes,
        )
        for c in chapters
    ]


def create_chapter(db, book_id: int, payload: BookChapterCreate) -> BookChapterRead | None:
    book = repo.get_book(db, book_id)
    if not book:
        return None
    chapter = repo.create_chapter(db, {"book_id": book_id, **payload.model_dump()})
    return BookChapterRead(
        id=chapter.id,
        book_id=chapter.book_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        content=chapter.content,
        reading_time_minutes=chapter.reading_time_minutes,
    )


def update_chapter(db, chapter_id: int, payload: BookChapterUpdate) -> BookChapterRead | None:
    chapter = repo.get_chapter(db, chapter_id)
    if not chapter:
        return None
    updated = repo.update_chapter(db, chapter, payload.model_dump(exclude_none=True))
    return BookChapterRead(
        id=updated.id,
        book_id=updated.book_id,
        chapter_number=updated.chapter_number,
        title=updated.title,
        content=updated.content,
        reading_time_minutes=updated.reading_time_minutes,
    )


def delete_chapter(db, chapter_id: int) -> None:
    repo.delete_chapter(db, chapter_id)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize(db, book) -> BookRead:
    chapters = repo.list_chapters(db, book.id)
    total_time = sum(c.reading_time_minutes for c in chapters)
    return BookRead(
        id=book.id,
        title=book.title,
        author=book.author,
        description=book.description,
        cover_url=book.cover_url,
        category=book.category,
        language=book.language,
        published=book.published,
        sort_order=book.sort_order,
        chapter_count=len(chapters),
        total_reading_time=total_time,
    )


def _serialize_detail(db, book) -> BookRead:
    base = _serialize(db, book)
    chapters = repo.list_chapters(db, book.id)
    chapter_reads = [
        BookChapterRead(
            id=c.id,
            book_id=c.book_id,
            chapter_number=c.chapter_number,
            title=c.title,
            content=c.content,
            reading_time_minutes=c.reading_time_minutes,
        )
        for c in chapters
    ]
    return BookRead(
        **base.model_dump(),
        chapters=chapter_reads,
    )
