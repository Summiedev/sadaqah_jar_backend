from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Charity(Base):
    __tablename__ = "charities"
    __table_args__ = (
        Index(
            "ix_charities_verified_active_category",
            "is_verified",
            "is_active",
            "category",
        ),
        Index(
            "ix_charities_verified_active_featured",
            "is_verified",
            "is_active",
            "is_featured",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    website_url: Mapped[str] = mapped_column(String, nullable=False)

    category: Mapped[str | None] = mapped_column(String, nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    donation_intents = relationship("DonationIntent", back_populates="charity")
