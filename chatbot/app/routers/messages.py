"""
Messages router — send chat messages (creates conversation when needed).
"""
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies.services import get_conversation_chat_service
from ..dependencies.auth import get_request_user_id
from ..schemas.conversation import SendMessageRequest, SendMessageResponse
from ..services.conversation_chat_service import (
    ConversationChatServiceProtocol,
    ConversationNotFoundError,
)

router = APIRouter(prefix="/api/conversations", tags=["messages"])


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
