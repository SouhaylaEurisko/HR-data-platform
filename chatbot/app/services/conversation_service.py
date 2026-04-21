"""
Conversation service — business logic for conversation operations.
"""
from typing import Optional, List, Protocol

from ..models.conversation import Conversation, ConversationMessage
from ..schemas.conversation import ConversationMessageRead, ConversationWithMessages
from ..repository.conversation_repository import ConversationRepositoryProtocol


class ConversationServiceProtocol(Protocol):
    def create_conversation(
        self,
        title: Optional[str] = "New chat",
        user_id: Optional[int] = None,
    ) -> Conversation: ...
    def update_conversation_title(self, conversation_id: int, title: str) -> bool: ...
    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Conversation]: ...
    def list_conversations(self, user_id: int, limit: int = 100) -> List[Conversation]: ...
    def get_conversation_read(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[ConversationWithMessages]: ...
    def delete_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> bool: ...
    def add_message_to_conversation(
        self,
        conversation_id: int,
        content: str,
        sender: str,
        response_data: Optional[dict] = None,
    ) -> ConversationMessage: ...


class ConversationService:
    def __init__(self, repo: ConversationRepositoryProtocol) -> None:
        self._repo = repo

    def create_conversation(
        self,
        title: Optional[str] = "New chat",
        user_id: Optional[int] = None,
    ) -> Conversation:
        return self._repo.create_conversation(title=title, user_id=user_id)

    def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        return self._repo.update_conversation_title(
            conversation_id=conversation_id,
            title=title,
        )

    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Conversation]:
        return self._repo.get_conversation_by_id(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    def list_conversations(self, user_id: int, limit: int = 100) -> List[Conversation]:
        return self._repo.list_conversations(user_id=user_id, limit=limit)

    def get_conversation_read(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[ConversationWithMessages]:
        conversation = self.get_conversation_by_id(conversation_id, user_id=user_id)
        if conversation is None:
            return None

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
            user_account_id=conversation.user_account_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
        )

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> bool:
        return self._repo.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    def add_message_to_conversation(
        self,
        conversation_id: int,
        content: str,
        sender: str,
        response_data: Optional[dict] = None,
    ) -> ConversationMessage:
        return self._repo.add_message_to_conversation(
            conversation_id=conversation_id,
            content=content,
            sender=sender,
            response_data=response_data,
        )
