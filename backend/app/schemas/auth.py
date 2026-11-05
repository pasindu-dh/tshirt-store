from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError("Name cannot be blank")

        return stripped


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    email_verified: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class PasswordForgotRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)

    model_config = ConfigDict(extra="forbid")


class EmailVerificationResendRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")


class MessageOut(BaseModel):
    message: str


class AuthConfigOut(BaseModel):
    email_verification_required: bool
    email_verification_available: bool
    password_reset_available: bool
