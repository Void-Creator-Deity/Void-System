"""HTTP contracts for identity and account workflows."""
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


Password = Annotated[str, Field(min_length=8, max_length=72)]


class UserRegister(BaseModel):
    """Public registration payload."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Password
    username: str = Field(..., min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("档案代号不能为空")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过 72 个字节")
        return value


class LoginRequest(BaseModel):
    """JSON login payload for first-party web and mobile clients."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=72)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("邮箱或档案代号不能为空")
        return value.lower() if "@" in value else value


class RefreshTokenRequest(BaseModel):
    """Refresh payload kept out of query strings and logs."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=1, max_length=4096)


class ProfileUpdateRequest(BaseModel):
    """User-editable profile fields."""

    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=1, max_length=50)
    learning_goal: Optional[str] = Field(default=None, max_length=500)
    specialization: Optional[str] = Field(default=None, max_length=500)

    @field_validator("username", "learning_goal", "specialization")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value

    @model_validator(mode="after")
    def require_one_change(self) -> "ProfileUpdateRequest":
        if all(
            value is None
            for value in (
                self.email,
                self.username,
                self.learning_goal,
                self.specialization,
            )
        ):
            raise ValueError("请至少提供一项要更新的资料")
        return self


class PasswordChangeRequest(BaseModel):
    """Authenticated password rotation request."""

    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(..., min_length=1, max_length=72)
    new_password: Password

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码长度不能超过 72 个字节")
        return value


class LogoutRequest(BaseModel):
    """Logout options. A normal logout revokes only the current device session."""

    model_config = ConfigDict(extra="forbid")

    all_sessions: bool = False
