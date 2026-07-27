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
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)
        self.code = "auth.invalid_credentials"


class InvalidTokenException(AuthenticationException):
    def __init__(self, message: str = "This link is invalid or has expired"):
        super().__init__(message)
        self.code = "auth.invalid_token"


class EmailTakenException(ConflictException):
    def __init__(self, message: str = "This email is already registered"):
        super().__init__(message)
        self.code = "auth.email_taken"


class UsernameTakenException(ConflictException):
    def __init__(self, message: str = "This username is already taken"):
        super().__init__(message)
        self.code = "auth.username_taken"


class ForbiddenException(AuthenticationException):
    def __init__(self, message: str = "Operation not permitted"):
        super().__init__(message)


class GoogleOAuthException(AuthenticationException):
    def __init__(self, message: str = "Google authentication failed. Please try again."):
        super().__init__(message)
        self.code = "auth.invalid_google_token"
