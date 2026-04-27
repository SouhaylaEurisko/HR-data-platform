"""Title Agent — generates short conversation titles via LLM."""
from .models import TitleResult
from .prompts import TITLE_GENERATION_PROMPT
from ...utils.pydantic_ai_client import build_agent, run_typed


class TitleAgent:
    def __init__(self):
        self._agent = build_agent(
            TitleResult,
            TITLE_GENERATION_PROMPT,
            temperature=0.5,
        )

    async def generate(self, first_message: str) -> str:
        """Return a 2-4 word title for the conversation."""
        try:
            result = await run_typed(
                self._agent,
                first_message,
                context="Title generation",
            )
            title = result.title.strip().strip('"\'')
            words = title.split()[:4]
            return " ".join(words) or "New Chat"
        except Exception:
            return "New Chat"
