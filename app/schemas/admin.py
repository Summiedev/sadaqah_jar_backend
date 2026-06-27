from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from datetime import date


class CharityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website_url: HttpUrl
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class CharityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
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
