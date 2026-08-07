"""Book bookmark model."""

from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mixins import TimestampMixin
from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BookBookmark(Base, TimestampMixin):
    __tablename__ = "book_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    book = relationship("Book", back_populates="bookmarks")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_book_bookmark_user_book"),
    )
