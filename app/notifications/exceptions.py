"""Notifications domain exceptions."""

from app.core.exceptions import (
    AppException,
    ConflictException,
    ResourceNotFoundException,
)


class NotificationException(AppException):
    pass


class NotificationNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Notification not found"):
        super().__init__(message)


class TemplateNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Template not found"):
        super().__init__(message)


class TemplateConflictException(ConflictException):
    def __init__(self, message: str = "Template already exists"):
        super().__init__(message)


class DeviceNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Device not found"):
        super().__init__(message)
