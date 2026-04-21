"""
Conversations router — handles conversation management endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies.services import (
    get_conversation_service,
    get_conversation_chat_service,
)
from ..dependencies.auth import get_request_user_id
from ..models.conversation import (
    ConversationRead,
    ConversationWithMessages,
    SendMessageRequest,
    SendMessageResponse,
)
from ..services.conversation_service import ConversationServiceProtocol
from ..services.conversation_chat_service import (
    ConversationChatServiceProtocol,
    ConversationNotFoundError,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationRead])
async def list_conversations_endpoint(
    user_id: int = Depends(get_request_user_id),
    conversation_service: ConversationServiceProtocol = Depends(get_conversation_service),
):
    """
    List all conversations.
    """
    conversations = conversation_service.list_conversations(user_id=user_id)
    return [ConversationRead.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation_endpoint(
    conversation_id: int,
    user_id: int = Depends(get_request_user_id),
    conversation_service: ConversationServiceProtocol = Depends(get_conversation_service),
):
    """
    Get a conversation by ID with all its messages.
    """
    conversation = conversation_service.get_conversation_read(conversation_id, user_id=user_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    return conversation


@router.post("/send", response_model=SendMessageResponse)
async def send_message_endpoint(
    request: SendMessageRequest,
    user_id: int = Depends(get_request_user_id),
    chat_service: ConversationChatServiceProtocol = Depends(get_conversation_chat_service),
):
    """
    Send a message to a conversation (creates conversation if needed).
    """
    try:
        result = await chat_service.handle_send_message(
            content=request.content,
            sender=request.sender,
            conversation_id=request.conversation_id,
            user_id=user_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return SendMessageResponse(**result)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(
    conversation_id: int,
    user_id: int = Depends(get_request_user_id),
    conversation_service: ConversationServiceProtocol = Depends(get_conversation_service),
):
    """
    Delete a conversation and all its messages.
    """
    deleted = conversation_service.delete_conversation(
        conversation_id,
        user_id=user_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
