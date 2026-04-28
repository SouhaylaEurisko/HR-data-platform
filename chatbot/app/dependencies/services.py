"""
Service dependency providers.
"""
from fastapi import Depends

from ..repository.conversation_repository import ConversationRepositoryProtocol
from ..repository.user_repository import UserRepositoryProtocol
from ..agents.flow_agent import FlowAgent
from ..agents.title_agent import TitleAgent
from ..services.conversation_service import ConversationService, ConversationServiceProtocol
from ..services.conversation_chat_service import (
    ConversationChatService,
    ConversationChatServiceProtocol,
)
from ..services.message_service import MessageService, MessageServiceProtocol
from .agents import get_flow_agent, get_title_agent
from .repositories import get_conversation_repository, get_user_repository


def get_conversation_service(
    conversation_repo: ConversationRepositoryProtocol = Depends(get_conversation_repository),
) -> ConversationServiceProtocol:
    return ConversationService(conversation_repo)


def get_message_service(
    conversation_repo: ConversationRepositoryProtocol = Depends(get_conversation_repository),
    user_repo: UserRepositoryProtocol = Depends(get_user_repository),
    flow_agent: FlowAgent = Depends(get_flow_agent),
    title_agent: TitleAgent = Depends(get_title_agent),
) -> MessageServiceProtocol:
    return MessageService(
        conversation_repo=conversation_repo,
        user_repo=user_repo,
        flow_agent=flow_agent,
        title_agent=title_agent,
    )


def get_conversation_chat_service(
    conversation_service: ConversationServiceProtocol = Depends(get_conversation_service),
    message_service: MessageServiceProtocol = Depends(get_message_service),
) -> ConversationChatServiceProtocol:
    return ConversationChatService(
        conversation_service=conversation_service,
        message_service=message_service,
    )
