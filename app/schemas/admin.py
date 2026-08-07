from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from datetime import date


class CharityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    donation_type: str = Field(default="external", pattern="^(personal|external)$")
    website_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=255)
    case_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
    target_amount: Decimal | None = Field(default=None, ge=0)
    amount_raised: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="NGN", max_length=8)
    image_urls: list[str] | None = None
    evidence: str | None = Field(default=None, max_length=8000)
    evidence_urls: list[str] | None = None
    contact_info: str | None = Field(default=None, max_length=2000)
    status: str = Field(
        default="active", pattern="^(active|goal_reached|completed|closed)$"
    )
    deadline: date | None = None
    is_published: bool = True
    is_featured: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("website_url")
    @classmethod
    def validate_url_for_external(cls, value: HttpUrl | None, info):
        donation_type = info.data.get("donation_type", "external")
        if donation_type == "external" and value is None:
            raise ValueError("External donations need a donation URL")
        return value


class CharityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=255)
    donation_type: str | None = Field(default=None, pattern="^(personal|external)$")
    case_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
    target_amount: Decimal | None = Field(default=None, ge=0)
    amount_raised: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    image_urls: list[str] | None = None
    evidence: str | None = Field(default=None, max_length=8000)
    evidence_urls: list[str] | None = None
    contact_info: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(
        default=None, pattern="^(active|goal_reached|completed|closed)$"
    )
    deadline: date | None = None
    is_published: bool | None = None
    is_verified: bool | None = None
    is_active: bool | None = None
    is_featured: bool | None = None

    model_config = ConfigDict(extra="forbid")


class EvidenceCreate(BaseModel):
    act_id: int = Field(gt=0)
    source_type: str = Field(min_length=1, max_length=50)
    reference: str = Field(min_length=1, max_length=255)
    arabic_text: str | None = None
    english_text: str | None = None
    grade: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")


class EvidenceUpdate(BaseModel):
    act_id: int | None = Field(default=None, gt=0)
    source_type: str | None = Field(default=None, min_length=1, max_length=50)
    reference: str | None = Field(default=None, min_length=1, max_length=255)
    arabic_text: str | None = None
    english_text: str | None = None
    grade: str | None = Field(default=None, max_length=50)
    is_verified: bool | None = None

    model_config = ConfigDict(extra="forbid")


class LeaderboardSeasonUpsert(BaseModel):
    start_date: date
    end_date: date

    model_config = ConfigDict(extra="forbid")
