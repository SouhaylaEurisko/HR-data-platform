"""
Service dependency providers.
"""
from fastapi import Depends

from ..repository.conversation_repository import ConversationRepositoryProtocol
from ..repository.user_repository import UserRepositoryProtocol
from ..services.conversation_service import ConversationService, ConversationServiceProtocol
from ..services.conversation_chat_service import (
    ConversationChatService,
    ConversationChatServiceProtocol,
)
from ..services.message_service import MessageService, MessageServiceProtocol
from .repositories import get_conversation_repository, get_user_repository


def get_conversation_service(
    conversation_repo: ConversationRepositoryProtocol = Depends(get_conversation_repository),
) -> ConversationServiceProtocol:
    return ConversationService(conversation_repo)


def get_message_service(
    conversation_repo: ConversationRepositoryProtocol = Depends(get_conversation_repository),
    user_repo: UserRepositoryProtocol = Depends(get_user_repository),
) -> MessageServiceProtocol:
    return MessageService(
        conversation_repo=conversation_repo,
        user_repo=user_repo,
    )


def get_conversation_chat_service(
    conversation_service: ConversationServiceProtocol = Depends(get_conversation_service),
    message_service: MessageServiceProtocol = Depends(get_message_service),
) -> ConversationChatServiceProtocol:
    return ConversationChatService(
        conversation_service=conversation_service,
        message_service=message_service,
    )
