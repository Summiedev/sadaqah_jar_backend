from sqlalchemy import Boolean, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from enum import Enum as PyEnum


class SadaqahCategory(PyEnum):
    general = "general"
    dhikr = "dhikr"
    community = "community"
    donation = "donation"
    kindness = "kindness"
    family = "family"
    knowledge = "knowledge"
    environment = "environment"
    character = "character"


class SadaqahAct(Base):
    __tablename__ = "sadaqah_acts"
    __table_args__ = (
        Index("ix_sadaqah_acts_verified_ramadan", "verified", "is_ramadan_only"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[SadaqahCategory] = mapped_column(
        Enum(SadaqahCategory, native_enum=False), nullable=False
    )

    verified: Mapped[bool] = mapped_column(Boolean, default=True)

    is_ramadan_only: Mapped[bool] = mapped_column(Boolean, default=False)

    ramadan_multiplier: Mapped[int] = mapped_column(Integer, default=1)

    difficulty: Mapped[int] = mapped_column(Integer, default=1)

    reward_weight: Mapped[int] = mapped_column(Integer, default=1)

    estimated_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    evidences = relationship(
        "Evidence", cascade="all, delete-orphan", back_populates="act"
    )
    logs = relationship("SadaqahLog", backref="act")
