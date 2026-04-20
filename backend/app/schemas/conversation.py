"""Conversation / message API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    content: str
    sender: str
    response_data: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    sender: str  # 'user' | 'assistant'
    response_data: Optional[dict[str, Any]] = None


class ConversationRead(BaseModel):
    id: int
    user_account_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationWithMessages(ConversationRead):
    messages: list[MessageRead] = []
