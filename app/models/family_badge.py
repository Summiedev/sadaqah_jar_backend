# app/models/family_badge.py

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FamilyBadge(Base):
    __tablename__ = "family_badges"

    id: Mapped[int] = mapped_column(primary_key=True)

    family_id: Mapped[int] = mapped_column(
        ForeignKey("family_jars.id")
    )

    badge_id: Mapped[int] = mapped_column(
        ForeignKey("badges.id")
    )