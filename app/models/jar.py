from typing import Optional

from sqlalchemy import Integer, DateTime, ForeignKey, Column   
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.db.base import Base

class Jar(Base):
    __tablename__ = "jars"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )

    current_stars: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    capacity: Mapped[int] = mapped_column(
        Integer,
        default=33
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    user = relationship("User", back_populates="jars")