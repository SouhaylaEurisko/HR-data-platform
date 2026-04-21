"""Conversation SQLAlchemy ORM models."""

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



