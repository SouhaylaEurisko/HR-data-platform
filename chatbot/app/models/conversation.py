"""
Conversation models — SQLAlchemy ORM models and Pydantic schemas.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


# ──────────────────────────────────────────────
# SQLAlchemy ORM Models
# ──────────────────────────────────────────────

class Conversation(Base):
    """SQLAlchemy model for conversation records."""
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    # User ID from the main backend (user_account.id), passed via X-User-Id header.
    # Explicit name so INSERT uses user_account_id (DB column), not user_id.
    user_account_id = Column("user_account_id", Integer, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationship to messages
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    """SQLAlchemy model for conversation messages."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    sender = Column(String(50), nullable=False)  # 'user' or 'assistant'
    response_data = Column(JSONB, nullable=True)  # Store ChatResponse data (JSONB for PostgreSQL)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────

class ConversationBase(BaseModel):
    """Base schema with common conversation fields."""
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    # Optional: allow creating with explicit user_id via API if ever needed
    user_account_id: Optional[int] = None


class ConversationRead(ConversationBase):
    """Schema for reading conversation data."""
    id: int
    user_account_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationMessageRead(BaseModel):
    """Schema for reading conversation message data."""
    id: int
    conversation_id: int
    content: str
    sender: str
    response: Optional[Dict[str, Any]] = None  # ChatResponse data
    created_at: datetime

    class Config:
        from_attributes = True
    
    def model_post_init(self, __context) -> None:
        """Map response_data to response field."""
        if hasattr(self, 'response_data') and self.response_data:
            self.response = self.response_data


class ConversationWithMessages(ConversationRead):
    """Schema for conversation with its messages."""
    messages: List[ConversationMessageRead] = []


class SendMessageRequest(BaseModel):
    """Schema for sending a message."""
    content: str
    sender: str  # 'user' or 'assistant'
    conversation_id: Optional[int] = None


class SendMessageResponse(BaseModel):
    """Schema for message send response."""
    reply: str
    conversation_id: int
    response: Optional[Dict[str, Any]] = None  # Full ChatResponse data
