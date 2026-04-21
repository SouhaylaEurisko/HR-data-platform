from __future__ import annotations  

from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import BaseModel


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
