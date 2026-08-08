"""Journey domain Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReflectionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    mood: str = Field(..., min_length=1, max_length=64)
    is_private: bool = False
    date: datetime | None = None
    request_id: str | None = None


class ReflectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    mood: str | None = Field(default=None, min_length=1, max_length=64)
    is_private: bool | None = None
    date: datetime | None = None


class ReflectionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    mood: str
    is_private: bool
    date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdhkarProgressResponse(BaseModel):
    id: int
    adhkar_id: int
    count: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdhkarFavoriteResponse(BaseModel):
    id: int
    adhkar_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReadingProgressResponse(BaseModel):
    book_id: int
    chapter_number: int
    last_read_at: datetime | None = None

    model_config = {"from_attributes": True}


class QuranProgressPayload(BaseModel):
    surah_id: int = Field(..., ge=1, le=114)
    verse_key: str = Field(..., min_length=3, max_length=16)
    page: int = Field(..., ge=1, le=604)


class QuranProgressResponse(QuranProgressPayload):
    last_read_at: datetime

    model_config = {"from_attributes": True}
