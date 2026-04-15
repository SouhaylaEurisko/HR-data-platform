"""Conversation / message API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    role: str  # 'user' | 'assistant' | 'system'
    content: str


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
