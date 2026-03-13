"""
Conversations router — handles conversation management endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.conversation import (
    ConversationRead,
    ConversationWithMessages,
    SendMessageRequest,
    SendMessageResponse,
    ConversationMessageRead,
)
from ..services.conversation_service import (
    create_conversation,
    get_conversation_by_id,
    list_conversations,
    delete_conversation,
    add_message_to_conversation,
    update_conversation_title,
)
from ..services.message_service import process_chat_message, generate_conversation_title

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationRead])
async def list_conversations_endpoint(
    db: Session = Depends(get_db),
):
    """
    List all conversations.
    """
    conversations = list_conversations(db)
    return [ConversationRead.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a conversation by ID with all its messages.
    """
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    # Convert messages to read format
    messages = [
        ConversationMessageRead(
            id=m.id,
            conversation_id=m.conversation_id,
            content=m.content,
            sender=m.sender,
            response=m.response_data,
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]
    
    return ConversationWithMessages(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.post("/send", response_model=SendMessageResponse)
async def send_message_endpoint(
    request: SendMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message to a conversation (creates conversation if needed).
    """
    # Get or create conversation
    is_new_conversation = False
    if request.conversation_id:
        conversation = get_conversation_by_id(db, request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found"
            )
        conversation_id = conversation.id
        # Check if this is the first message (title is "New chat" or None)
        is_new_conversation = (conversation.title is None or conversation.title == "New chat")
    else:
        # Create new conversation with default title
        conversation = create_conversation(db, title="New chat")
        conversation_id = conversation.id
        is_new_conversation = True
    
    # Add user message
    user_message = add_message_to_conversation(
        db=db,
        conversation_id=conversation_id,
        content=request.content,
        sender=request.sender,
    )
    
    # Generate title for new conversations based on first user message
    if is_new_conversation:
        title = await generate_conversation_title(request.content)
        update_conversation_title(db, conversation_id, title)
    
    # Process message and get AI response
    response_data = await process_chat_message(
        message=request.content,
        conversation_id=conversation_id,
        db=db,
    )
    
    # Add assistant response
    assistant_message = add_message_to_conversation(
        db=db,
        conversation_id=conversation_id,
        content=response_data["reply"],
        sender="assistant",
        response_data=response_data.get("response"),
    )
    
    return SendMessageResponse(
        reply=response_data["reply"],
        conversation_id=conversation_id,
        response=response_data.get("response"),
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a conversation and all its messages.
    """
    deleted = delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
