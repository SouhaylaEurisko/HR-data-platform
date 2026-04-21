"""
Conversation chat service — orchestrates conversation send-message workflow.
"""
from typing import Any, Dict, Optional, Protocol

from .conversation_service import ConversationServiceProtocol
from .message_service import MessageServiceProtocol


class ConversationNotFoundError(Exception):
    """Raised when the target conversation does not exist for the user."""


class ConversationChatServiceProtocol(Protocol):
    async def handle_send_message(
        self,
        *,
        content: str,
        sender: str,
        conversation_id: Optional[int],
        user_id: int,
    ) -> Dict[str, Any]: ...


class ConversationChatService:
    def __init__(
        self,
        conversation_service: ConversationServiceProtocol,
        message_service: MessageServiceProtocol,
    ) -> None:
        self._conversation_service = conversation_service
        self._message_service = message_service

    async def handle_send_message(
        self,
        *,
        content: str,
        sender: str,
        conversation_id: Optional[int],
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Send a user message, run AI processing, persist assistant response.
        """
        resolved_conversation_id: int
        is_new_conversation = False

        if conversation_id:
            conversation = self._conversation_service.get_conversation_by_id(
                conversation_id,
                user_id=user_id,
            )
            if conversation is None:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            resolved_conversation_id = conversation.id
            is_new_conversation = (
                conversation.title is None or conversation.title == "New chat"
            )
        else:
            conversation = self._conversation_service.create_conversation(
                title="New chat",
                user_id=user_id,
            )
            resolved_conversation_id = conversation.id
            is_new_conversation = True

        self._conversation_service.add_message_to_conversation(
            conversation_id=resolved_conversation_id,
            content=content,
            sender=sender,
        )

        if is_new_conversation:
            title = await self._message_service.generate_conversation_title(content)
            self._conversation_service.update_conversation_title(
                resolved_conversation_id,
                title,
            )

        response_data = await self._message_service.process_chat_message(
            message=content,
            conversation_id=resolved_conversation_id,
            user_id=user_id,
        )

        self._conversation_service.add_message_to_conversation(
            conversation_id=resolved_conversation_id,
            content=response_data["reply"],
            sender="assistant",
            response_data=response_data.get("response"),
        )

        return {
            "reply": response_data["reply"],
            "conversation_id": resolved_conversation_id,
            "response": response_data.get("response"),
        }
