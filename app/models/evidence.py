from sqlalchemy import Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    act_id: Mapped[int] = mapped_column(
        ForeignKey("sadaqah_acts.id"),
        nullable=False
    )

    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    # "QURAN" or "HADITH"

    reference: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
   

    arabic_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    english_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    grade: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )
    # Sahih / Hasan etc

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    act = relationship(
        "SadaqahAct",
        back_populates="evidences"
    )