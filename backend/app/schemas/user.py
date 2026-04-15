"""User-related HTTP request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from ..constants import Auth


class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(BaseModel):
    """Internal / service layer: create user with explicit org (used by admin invite)."""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    organization_id: int = 1
    role: Optional[str] = Auth.HR_MANAGER_ROLE

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("First and last name are required")
        return str(v).strip()


class AdminUserCreate(BaseModel):
    """HR manager creates a user in their organization (no organization_id in body)."""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(
        default=Auth.HR_MANAGER_ROLE,
        description=f"{Auth.HR_MANAGER_ROLE} or {Auth.HR_VIEWER_ROLE}",
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("First and last name are required")
        return str(v).strip()

    @field_validator("role")
    @classmethod
    def role_must_be_allowed(cls, v: str) -> str:
        allowed = frozenset({Auth.HR_MANAGER_ROLE, Auth.HR_VIEWER_ROLE})
        if v not in allowed:
            raise ValueError(f"role must be one of: {', '.join(sorted(allowed))}")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class UserRead(UserBase):
    id: int
    organization_id: int
    role: str
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int
