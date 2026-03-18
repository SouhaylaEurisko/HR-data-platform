"""
Conversation service — business logic for conversation operations.
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationCreate,
    ConversationRead,
    ConversationWithMessages,
    ConversationMessageRead,
    SendMessageRequest,
    SendMessageResponse,
)


def create_conversation(
    db: Session,
    title: Optional[str] = "New chat",
    user_id: Optional[int] = None,
) -> Conversation:
    """
    Create a new conversation.
    
    Args:
        db: Database session
        title: Optional conversation title (defaults to "New chat")
        
    Returns:
        Conversation instance
    """

    if user_id is None:
        raise ValueError("user_id is required to create a conversation")
    conversation = Conversation(title=title, user_account_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def update_conversation_title(db: Session, conversation_id: int, title: str) -> bool:
    """
    Update a conversation's title.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        title: New title
        
    Returns:
        True if updated, False if conversation not found
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation is None:
        return False
    
    conversation.title = title
    db.commit()
    return True


def get_conversation_by_id(
    db: Session,
    conversation_id: int,
    user_id: Optional[int] = None,
) -> Optional[Conversation]:
    """
    Get a conversation by ID with its messages.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        
    Returns:
        Conversation instance if found, None otherwise
    """
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if user_id is not None:
        query = query.filter(Conversation.user_account_id == user_id)
    return query.first()


def list_conversations(
    db: Session,
    user_id: int,
    limit: int = 100,
) -> List[Conversation]:
    """
    List all conversations, ordered by most recent first.
    
    Args:
        db: Database session
        limit: Maximum number of conversations to return
        
    Returns:
        List of Conversation instances
    """
    return (
        db.query(Conversation)
        .filter(Conversation.user_account_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .all()
    )


def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: Optional[int] = None,
) -> bool:
    """
    Delete a conversation and all its messages.
    
    Args:
        db: Database session
        conversation_id: Conversation ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    conversation = get_conversation_by_id(db, conversation_id, user_id=user_id)
    if conversation is None:
        return False
    
    db.delete(conversation)
    db.commit()
    return True


def add_message_to_conversation(
    db: Session,
    conversation_id: int,
    content: str,
    sender: str,
    response_data: Optional[dict] = None,
) -> ConversationMessage:
    """
    Add a message to a conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        content: Message content
        sender: Message sender ('user' or 'assistant')
        response_data: Optional response data (ChatResponse)
        
    Returns:
        ConversationMessage instance
    """
    message = ConversationMessage(
        conversation_id=conversation_id,
        content=content,
        sender=sender,
        response_data=response_data,
    )
    db.add(message)
    
    # Update conversation's updated_at timestamp
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message
