"""
User repository — database access for user metadata.
"""
from typing import Optional, Union, Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session


class UserRepositoryProtocol(Protocol):
    def get_user_first_name(self, user_id: Optional[Union[int, str]]) -> Optional[str]: ...


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_user_first_name(self, user_id: Optional[Union[int, str]]) -> Optional[str]:
        """Fetch first_name for a given user_account ID."""
        if user_id is None:
            return None

        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None

        row = self._db.execute(
            text("SELECT first_name FROM user_account WHERE id = :uid LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not row:
            return None

        first_name = (row.get("first_name") or "").strip()
        return first_name or None
