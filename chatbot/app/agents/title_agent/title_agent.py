"""Title Agent — generates short conversation titles via LLM."""

from typing import Any

from pydantic_ai import Agent

from .models import TitleResult
from ...utils.pydantic_ai_client import PydanticAIClient


class TitleAgent:
    def __init__(
        self,
        agent: Agent[Any, TitleResult],
        ai_client: PydanticAIClient,
    ):
        self._agent = agent
        self._ai_client = ai_client

    async def generate(self, first_message: str) -> str:
        """Return a 2-4 word title for the conversation."""
        try:
            result = await self._ai_client.run_typed(
                self._agent,
                first_message,
                context="Title generation",
            )
            title = result.title.strip().strip('"\'')
            words = title.split()[:4]
            return " ".join(words) or "New Chat"
        except Exception:
            return "New Chat"
