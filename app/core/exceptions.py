"""Centralized exception hierarchy for Mizan.

Every domain exception inherits from AppException.
The global exception handler in app/main.py maps these to HTTP status codes.
"""


class AppException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__("validation.error", message, details)


class AuthenticationException(AppException):
    def __init__(
        self, message: str = "Authentication required", details: dict | None = None
    ):
        super().__init__("auth.authentication_required", message, details)


class AuthorizationException(AppException):
    def __init__(self, message: str = "Permission denied", details: dict | None = None):
        super().__init__("auth.permission_denied", message, details)


class ResourceNotFoundException(AppException):
    def __init__(
        self, message: str = "Resource not found", details: dict | None = None
    ):
        super().__init__("resource.not_found", message, details)


class ConflictException(AppException):
    def __init__(
        self, message: str = "Resource already exists", details: dict | None = None
    ):
        super().__init__("resource.conflict", message, details)


class BusinessRuleException(AppException):
    def __init__(
        self, message: str = "Business rule violated", details: dict | None = None
    ):
        super().__init__("business.rule_violated", message, details)


class RateLimitException(AppException):
    def __init__(
        self, message: str = "Rate limit exceeded", details: dict | None = None
    ):
        super().__init__("rate.limit_exceeded", message, details)


class ExternalServiceException(AppException):
    def __init__(
        self, message: str = "External service error", details: dict | None = None
    ):
        super().__init__("external.service_error", message, details)


class InfrastructureException(AppException):
    def __init__(
        self, message: str = "Infrastructure error", details: dict | None = None
    ):
        super().__init__("infrastructure.error", message, details)


class InternalServerException(AppException):
    def __init__(
        self, message: str = "Internal server error", details: dict | None = None
    ):
        super().__init__("internal.error", message, details)
