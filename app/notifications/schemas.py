"""Notifications domain Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    category: str | None
    title: str
    message: str
    action: str | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationTemplateCreate(BaseModel):
    key: str
    title_template: str
    message_template: str
    category: str
    strategy: str
    strategy_config: dict | None = None


class NotificationTemplateResponse(BaseModel):
    id: int
    key: str
    title_template: str
    message_template: str
    category: str
    strategy: str
    strategy_config: dict | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    category: str
    enabled: bool


class DeviceTokenRequest(BaseModel):
    device_id: str
    platform: str
    device_name: str | None = None
    app_version: str | None = None
    push_token: str | None = None
