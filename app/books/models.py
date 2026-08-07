"""Books domain models."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_format: Mapped[str | None] = mapped_column(
        String(16), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    published: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    chapters = relationship(
        "BookChapter", back_populates="book", cascade="all, delete-orphan"
    )
    pages = relationship(
        "BookPage",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="BookPage.page_number",
    )
    bookmarks = relationship(
        "BookBookmark", back_populates="book", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# BookChapter
# ---------------------------------------------------------------------------


class BookChapter(Base):
    __tablename__ = "book_chapters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reading_time_minutes: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    book = relationship("Book", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint("book_id", "chapter_number", name="uq_book_chapter_number"),
        Index("ix_book_chapters_book_order", "book_id", "chapter_number"),
    )


class BookPage(Base):
    __tablename__ = "book_pages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    image_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    book = relationship("Book", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("book_id", "page_number", name="uq_book_page_number"),
        Index("ix_book_pages_book_order", "book_id", "page_number"),
    )
