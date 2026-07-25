"""Journey domain exceptions."""

from app.core.exceptions import (
    AppException,
    ConflictException,
    ResourceNotFoundException,
)


class JourneyException(AppException):
    pass


class ReflectionNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Reflection not found"):
        super().__init__(message)


class ProgressNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "No progress recorded for this adhkar"):
        super().__init__(message)


class FavoriteConflictException(ConflictException):
    def __init__(self, message: str = "Already favorited"):
        super().__init__(message)


class FavoriteNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Favorite not found"):
        super().__init__(message)
