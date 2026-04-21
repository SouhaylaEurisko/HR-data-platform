"""
Repository dependency providers.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from ..config import get_db
from ..repository.conversation_repository import (
    ConversationRepository,
    ConversationRepositoryProtocol,
)
from ..repository.user_repository import UserRepository, UserRepositoryProtocol


def get_conversation_repository(
    db: Session = Depends(get_db),
) -> ConversationRepositoryProtocol:
    return ConversationRepository(db)


def get_user_repository(
    db: Session = Depends(get_db),
) -> UserRepositoryProtocol:
    return UserRepository(db)
