"""Chit Chat Agent — handles greetings, thanks, off-topic."""
from .models import ChitChatResult
from .prompts import CHITCHAT_PROMPT
from ...utils.llm_client import LLMClient


class ChitChatAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def respond(self, message: str) -> ChitChatResult:
        data = await self.llm.call(
            CHITCHAT_PROMPT,
            message,
            context="Chit-chat",
            temperature=0.7,
        )
        return ChitChatResult.model_validate(data)
