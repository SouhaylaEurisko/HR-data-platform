"""
Conversation repository — database access for conversations and messages.
"""
from datetime import datetime
from typing import Optional, List, Protocol

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.conversation import Conversation, ConversationMessage


class ConversationRepositoryProtocol(Protocol):
    @property
    def db(self) -> Session: ...
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
    def list_recent_messages(
        self,
        conversation_id: int,
        limit: int,
    ) -> List[ConversationMessage]: ...


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    @property
    def db(self) -> Session:
        return self._db

    def create_conversation(
        self,
        title: Optional[str] = "New chat",
        user_id: Optional[int] = None,
    ) -> Conversation:
        """Create and persist a new conversation."""
        if user_id is None:
            raise ValueError("user_id is required to create a conversation")

        conversation = Conversation(title=title, user_account_id=user_id)
        self._db.add(conversation)
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        """Update a conversation title."""
        conversation = self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return False

        conversation.title = title
        self._db.commit()
        return True

    def get_conversation_by_id(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Conversation]:
        """Fetch a conversation by ID, optionally scoped to a user."""
        query = self._db.query(Conversation).filter(Conversation.id == conversation_id)
        if user_id is not None:
            query = query.filter(Conversation.user_account_id == user_id)
        return query.first()

    def list_conversations(self, user_id: int, limit: int = 100) -> List[Conversation]:
        """List user conversations ordered by most recent update."""
        return (
            self._db.query(Conversation)
            .filter(Conversation.user_account_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .all()
        )

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> bool:
        """Delete a conversation and cascade-delete its messages."""
        conversation = self.get_conversation_by_id(conversation_id, user_id=user_id)
        if conversation is None:
            return False

        self._db.delete(conversation)
        self._db.commit()
        return True

    def add_message_to_conversation(
        self,
        conversation_id: int,
        content: str,
        sender: str,
        response_data: Optional[dict] = None,
    ) -> ConversationMessage:
        """Insert a message and touch the parent conversation timestamp."""
        message = ConversationMessage(
            conversation_id=conversation_id,
            content=content,
            sender=sender,
            response_data=response_data,
        )
        self._db.add(message)

        conversation = self.get_conversation_by_id(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(message)
        return message

    def list_recent_messages(
        self,
        conversation_id: int,
        limit: int,
    ) -> List[ConversationMessage]:
        """Return the most recent messages for a conversation in chronological order."""
        recent_desc = (
            self._db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
            .all()
        )
        return list(reversed(recent_desc))
