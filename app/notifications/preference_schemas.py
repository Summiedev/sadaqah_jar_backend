"""Notification preference Pydantic schemas."""

from pydantic import BaseModel, Field


class QuietHoursUpdate(BaseModel):
    enabled: bool = False
    start: str = "22:00"
    end: str = "07:00"


class NotificationPreferencesUpdate(BaseModel):
    all_enabled: bool | None = None
    frequency: str | None = Field(None, pattern="^(low|medium|high)$")
    categories: dict[str, bool] | None = None
    quiet_hours: QuietHoursUpdate | None = None


class NotificationPreferencesState(BaseModel):
    all_enabled: bool = True
    frequency: str = "medium"
    quiet_hours: QuietHoursUpdate = QuietHoursUpdate()
    categories: dict[str, bool] = {}
    category_labels: dict[str, str] = {}