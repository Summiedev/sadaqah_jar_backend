"""Family domain exceptions."""

from app.core.exceptions import (
    AppException,
    BusinessRuleException,  # noqa: F401 - re-exported for domain use
    ConflictException,
    ResourceNotFoundException,
)


class FamilyException(AppException):
    pass


class FamilyNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Family not found"):
        super().__init__(message)


class MemberNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Member not found"):
        super().__init__(message)


class InvitationNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Invitation not found"):
        super().__init__(message)


class InvalidInviteCodeException(ResourceNotFoundException):
    def __init__(self, message: str = "Invalid invite code"):
        super().__init__(message)


class GoalNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Goal not found"):
        super().__init__(message)


class MilestoneNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Milestone not found"):
        super().__init__(message)


class PrayerRequestNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Prayer request not found"):
        super().__init__(message)


class ReflectionNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Reflection not found"):
        super().__init__(message)


class SettingsNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Settings not found"):
        super().__init__(message)


class FamilyPermissionDeniedException(ResourceNotFoundException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message)


class GoalAlreadyCompletedException(ConflictException):
    def __init__(self, message: str = "Goal already completed"):
        super().__init__(message)


class InvitationExpiredException(ConflictException):
    def __init__(self, message: str = "Invitation expired"):
        super().__init__(message)
