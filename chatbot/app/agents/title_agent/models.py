"""Models for Title Agent."""
from pydantic import BaseModel


class TitleResult(BaseModel):
    title: str
