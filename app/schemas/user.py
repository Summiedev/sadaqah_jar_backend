from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must be at least 8 characters and include a letter and a number")
        return v


class UpdatePreferencesRequest(BaseModel):
    evidence_mode: bool | None = None
    friday_reminder: bool | None = None


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    email_verified: bool
    role: str
    avatar_data: str | None = None
    evidence_mode: bool
    friday_reminder: bool


class UserProfileUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    avatar_data: str | None = None


class ForgotPasswordResponse(BaseModel):
    message: str = "If an account with that email exists, a password reset link has been sent."
