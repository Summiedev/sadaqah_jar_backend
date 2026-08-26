"""Family domain exceptions."""

from app.core.exceptions import (
    AppException,
    BusinessRuleException,  # noqa: F401 - re-exported for domain use
    ConflictException,
    ResourceNotFoundException,
)


class FamilyException(AppException):
    pass


class FamilyNotFoundException(AppException):
    def __init__(self, message: str = "Family not found"):
        super().__init__("family.not_found", message)


class MemberNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Member not found"):
        super().__init__(message)


class InvitationNotFoundException(ResourceNotFoundException):
    def __init__(self, message: str = "Invitation not found"):
        super().__init__(message)


class InvalidInviteCodeException(AppException):
    def __init__(self, message: str = "Invalid invite code"):
        super().__init__("family.invalid_invite_code", message)


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


class FamilyPermissionDeniedException(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__("family.permission_denied", message)


class FamilyMembershipConflictException(AppException):
    def __init__(self, message: str = "You are already a member of this family"):
        super().__init__("family.membership_conflict", message)


class GoalAlreadyCompletedException(ConflictException):
    def __init__(self, message: str = "Goal already completed"):
        super().__init__(message)


class InvitationExpiredException(ConflictException):
    def __init__(self, message: str = "Invitation expired"):
        super().__init__(message)
