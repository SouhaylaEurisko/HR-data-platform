"""
UserAccount model — multi-tenant user with organization scope and role-based access.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, model_validator
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
    role = Column(String(50), default="hr_viewer", nullable=False)
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


class UserCreate(UserBase):
    password: str
    organization_id: int = 1
    role: Optional[str] = "hr_viewer"
    full_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def split_full_name(cls, data):
        """Backward compat: accept 'full_name' from old frontends."""
        if isinstance(data, dict) and data.get("full_name") and not data.get("first_name"):
            parts = data["full_name"].strip().split(" ", 1)
            data["first_name"] = parts[0]
            if len(parts) > 1:
                data["last_name"] = parts[1]
        return data


class UserRead(UserBase):
    id: int
    organization_id: int
    role: str
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str
