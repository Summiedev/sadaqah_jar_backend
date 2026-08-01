"""Journey domain models.

Only user-specific state is persisted here. Static Islamic content
(adhkar catalogue, categories) remains version-controlled in the
frontend bundle and is not stored relationally.
"""

from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.mixins import SoftDeleteMixin, TimestampMixin
from app.db.base import Base


class JourneyReflection(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "journey_reflections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str] = mapped_column(String(64), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("ix_journey_reflections_user_date", "user_id", "date"),
        UniqueConstraint("user_id", "request_id", name="uq_journey_reflection_request"),
    )


class JourneyAdhkarProgress(Base, TimestampMixin):
    __tablename__ = "journey_adhkar_progress"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adhkar_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "adhkar_id", name="uq_journey_adhkar_progress"
        ),
    )


class JourneyAdhkarFavorite(Base, TimestampMixin):
    __tablename__ = "journey_adhkar_favorites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adhkar_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "adhkar_id", name="uq_journey_adhkar_favorite"
        ),
    )


class JourneyReadingProgress(Base, TimestampMixin):
    __tablename__ = "journey_reading_progress"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    last_read_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "book_id", name="uq_journey_reading_progress"
        ),
    )
