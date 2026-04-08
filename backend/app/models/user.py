"""
UserAccount model — multi-tenant user with organization scope and role-based access.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


# ──────────────────────────────────────────────
# SQLAlchemy ORM Model
# ──────────────────────────────────────────────

class UserAccount(Base):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(String(50), default="hr_manager", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    organization = relationship("Organization", back_populates="users")
    conversations = relationship(
        "Conversation",
        back_populates="user_account",
        cascade="all, delete-orphan",
    )


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────

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
    role: Optional[str] = "hr_manager"

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
    role: str = Field(default="hr_manager", description="hr_manager or hr_viewer")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_names(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("First and last name are required")
        return str(v).strip()

    @field_validator("role")
    @classmethod
    def role_must_be_allowed(cls, v: str) -> str:
        allowed = frozenset({"hr_manager", "hr_viewer"})
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