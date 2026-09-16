"""API contracts for in-app broadcasts."""

from datetime import datetime

from pydantic import BaseModel, Field


class BroadcastCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    body: str = Field(..., min_length=1)
    image_url: str | None = Field(default=None, max_length=1024)
    cta_label: str | None = Field(default=None, max_length=80)
    cta_link: str | None = Field(default=None, max_length=1024)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    audience: str = Field(default="all", pattern="^(all|admins|verified)$")
    display_mode: str = Field(
        default="until_dismissed",
        pattern="^(once|once_per_session|until_dismissed|until_expiry)$",
    )
    is_active: bool = True


class BroadcastUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, min_length=1)
    image_url: str | None = Field(default=None, max_length=1024)
    cta_label: str | None = Field(default=None, max_length=80)
    cta_link: str | None = Field(default=None, max_length=1024)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    audience: str | None = Field(default=None, pattern="^(all|admins|verified)$")
    display_mode: str | None = Field(
        default=None,
        pattern="^(once|once_per_session|until_dismissed|until_expiry)$",
    )
    is_active: bool | None = None
