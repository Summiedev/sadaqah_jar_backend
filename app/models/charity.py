from datetime import date

from sqlalchemy import Boolean, Date, Index, Integer, JSON, Numeric, String, Text
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

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    donation_type: Mapped[str] = mapped_column(
        String(24), default="external", nullable=False, index=True
    )

    case_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    website_url: Mapped[str] = mapped_column(String, nullable=False)

    external_url: Mapped[str | None] = mapped_column(String, nullable=True)

    category: Mapped[str | None] = mapped_column(String, nullable=True)

    target_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    amount_raised: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)

    image_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    contact_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(24), default="active", nullable=False, index=True
    )

    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_published: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    donation_intents = relationship("DonationIntent", back_populates="charity")
