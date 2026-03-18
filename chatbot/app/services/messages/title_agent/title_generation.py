"""Title Agent — generates short conversation titles via LLM."""
from .models import TitleResult
from .prompts import TITLE_GENERATION_PROMPT
from ...utils.llm_client import LLMClient


class TitleAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate(self, first_message: str) -> str:
        """Return a 2-4 word title for the conversation."""
        try:
            data = await self.llm.call(
                TITLE_GENERATION_PROMPT,
                first_message,
                context="Title generation",
                temperature=0.5,
            )
            result = TitleResult.model_validate(data)
            title = result.title.strip().strip('"\'')
            # Safety: limit length
            words = title.split()[:4]
            return " ".join(words) or "New Chat"
        except Exception:
            return "New Chat"
