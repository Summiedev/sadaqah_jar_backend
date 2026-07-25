"""Sadaqah domain exceptions."""

from app.core.exceptions import (
    AppException,
    ConflictException,
    ResourceNotFoundException,
)


class SadaqahException(AppException):
    pass


class ActivityCompletionNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Activity completion not found"):
        super().__init__(message)


class ActivitySessionNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Activity session not found"):
        super().__init__(message)


class ActivityTypeNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Activity type not found"):
        super().__init__(message)


class DailyLimitExceededException(ConflictException):
    def __init__(self, message: str = "Daily limit exceeded for this activity"):
        super().__init__(message)
