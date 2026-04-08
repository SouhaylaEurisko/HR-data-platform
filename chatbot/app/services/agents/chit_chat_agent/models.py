"""Models for Chit Chat Agent."""
from pydantic import BaseModel


class ChitChatResult(BaseModel):
    reply: str
