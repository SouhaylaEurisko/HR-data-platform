"""
User models — SQLAlchemy ORM model and Pydantic schemas for authentication.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, DateTime, Integer, String, Boolean
from sqlalchemy.sql import func

from ..config.database import Base


# ──────────────────────────────────────────────
# SQLAlchemy ORM Model
# ──────────────────────────────────────────────

class User(Base):
    """SQLAlchemy model for user accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────

class UserBase(BaseModel):
    """Base schema with common user fields."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str


class UserRead(UserBase):
    """Schema for reading user data."""
    id: int
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for login request (OAuth2PasswordRequestForm compatible)."""
    username: str  # FastAPI OAuth2 expects 'username' field
    password: str
