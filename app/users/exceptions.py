"""Users domain exceptions."""

from app.core.exceptions import (
    AppException,
    AuthenticationException,
    ConflictException,
    ResourceNotFoundException,
)


class AuthException(AppException):
    pass


class InvalidCredentialsException(AuthenticationException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class InvalidTokenException(AuthenticationException):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class EmailTakenException(ConflictException):
    def __init__(self, message: str = "Email already registered"):
        super().__init__(message)
        self.code = "auth.email_taken"


class UsernameTakenException(ConflictException):
    def __init__(self, message: str = "Username already taken"):
        super().__init__(message)
        self.code = "auth.username_taken"


class ForbiddenException(ResourceNotFoundException):
    def __init__(self, message: str = "Operation not permitted"):
        super().__init__(message)
