from pydantic import BaseModel, EmailStr, field_validator, model_validator, Field

from app.users.models import Role, UserMode

PASSWORD_ERROR = (
    "Password must be at least 8 characters and include a letter and a number"
)


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError(PASSWORD_ERROR)
    if not any(c.isalpha() for c in v):
        raise ValueError(PASSWORD_ERROR)
    if not any(c.isdigit() for c in v):
        raise ValueError(PASSWORD_ERROR)
    return v


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("role")
    @classmethod
    def normalize_role(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.upper()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VerifyEmailOtpRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        code = value.strip()
        if len(code) != 6 or not code.isdigit():
            raise ValueError("Enter the six-digit code from your email")
        return code


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ResendVerificationRequest(BaseModel):
    email: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if "@" not in stripped or "." not in stripped.split("@")[-1]:
            raise ValueError("Please provide a valid email address")
        return stripped


class ResendVerificationResponse(BaseModel):
    message: str = (
        "If an account with that email exists and is not verified, a new verification code has been sent."
    )


class GoogleAuthRequest(BaseModel):
    id_token: str


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    email_verified: bool
    role: Role
    mode: UserMode
    first_name: str | None = None
    last_name: str | None = None
    avatar_data: str | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    locale: str | None = None
    evidence_mode: bool = False
    friday_reminder: bool = False
    general_notifications: bool = False
    last_active: str | None = None
    created_at: str | None = None


class UserProfileUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_data: str | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    locale: str | None = None

    @model_validator(mode="after")
    def coordinates_are_complete_and_valid(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return self


class UserModeUpdate(BaseModel):
    mode: UserMode


class AvatarUpdate(BaseModel):
    avatar_data: str | None = None


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


class UserPreferencesUpdate(BaseModel):
    theme: str | None = None
    language: str | None = None
    notification_preferences: dict | None = None
    reminder_preferences: dict | None = None
    accessibility_preferences: dict | None = None
    privacy_preferences: dict | None = None
    timezone: str | None = None
    evidence_mode: bool | None = None
    friday_reminder: bool | None = None
    general_notifications: bool | None = None


class UserPreferencesResponse(BaseModel):
    theme: str
    language: str
    notification_preferences: dict
    reminder_preferences: dict
    accessibility_preferences: dict
    privacy_preferences: dict
    timezone: str | None = None
    selected_mode: UserMode


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    id: int
    device_id: str | None
    created_at: str | None
    last_used_at: str | None
    expires_at: str | None
    is_current: bool = False


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    platform: str
    device_name: str | None
    app_version: str | None
    has_push_token: bool
    last_active: str | None
    created_at: str | None


class PushTokenRequest(BaseModel):
    device_id: str
    platform: str
    device_name: str | None = None
    app_version: str | None = None
    push_token: str | None = None
    # Accept both `time_zone` (frontend) and `timezone` here via alias.
    timezone: str | None = Field(None, alias="time_zone")
    # Frontend sends coords as {"latitude": xx, "longitude": yy}; accept it
    # and normalize into latitude/longitude fields.
    coords: dict | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in ("ios", "android", "web"):
            raise ValueError("platform must be 'ios', 'android', or 'web'")
        return value

    @field_validator("device_id")
    @classmethod
    def non_empty_device_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("device_id is required")
        return v.strip()

    @model_validator(mode="after")
    def coordinates_are_complete_and_valid(self):
        # If coords were provided as a dict, normalize into latitude/longitude.
        if self.coords is not None and isinstance(self.coords, dict):
            lat = self.coords.get("latitude") or self.coords.get("lat")
            lng = self.coords.get("longitude") or self.coords.get("lng")
            if lat is not None and lng is not None:
                try:
                    self.latitude = float(lat)
                    self.longitude = float(lng)
                except Exception:
                    raise ValueError("coords must contain numeric latitude and longitude")

        # If one coordinate is provided, require the other as well.
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return self


class DeviceUpdate(BaseModel):
    device_name: str | None = None
    push_token: str | None = None
    app_version: str | None = None


# ---------------------------------------------------------------------------
# Email / password recovery
# ---------------------------------------------------------------------------


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = (
        "If an account with that email exists, a password reset link has been sent."
    )


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# ---------------------------------------------------------------------------
# Email change
# ---------------------------------------------------------------------------


class RequestEmailChangeRequest(BaseModel):
    current_password: str
    new_email: EmailStr


class RequestEmailChangeResponse(BaseModel):
    message: str = "Verification email sent to your new address."
    pending: bool = True


class ConfirmEmailChangeRequest(BaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        token = v.strip()
        if len(token) != 6 or not token.isdigit():
            raise ValueError("Enter the six-digit code from your email")
        return token


class ConfirmEmailChangeResponse(BaseModel):
    message: str = "Email updated successfully."
    pending: bool = False
    access_token: str | None = None
    refresh_token: str | None = None


class PendingEmailChangeResponse(BaseModel):
    id: int
    new_email: EmailStr
    expires_at: str | None = None
    created_at: str | None = None
