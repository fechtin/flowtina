"""Authentication and user schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: str
    email: str
    name: str
    avatar: str | None = None
    language: str
    timezone: str
    is_admin: bool
    active: bool
    last_login_at: datetime | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=8)
    timezone: str | None = Field(default=None, max_length=64)
    avatar: str | None = Field(default=None, max_length=500)
