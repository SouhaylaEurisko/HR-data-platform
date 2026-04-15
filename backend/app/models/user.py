"""UserAccount ORM — multi-tenant user with organization scope and role-based access."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base
from ..constants import Auth


class UserAccount(Base):
    __tablename__ = "user_account"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(String(50), default=Auth.HR_MANAGER_ROLE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    organization = relationship("Organization", back_populates="users")
    conversations = relationship(
        "Conversation",
        back_populates="user_account",
        cascade="all, delete-orphan",
    )
