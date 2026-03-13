"""Intent Classifier Agent — pure-LLM intent routing."""
from .models import IntentClassificationResult
from .prompts import INTENT_CLASSIFICATION_PROMPT
from ...utils.llm_client import LLMClient


class IntentClassifierAgent:
    """Classifies user messages into one of the supported intents."""

    def __init__(self):
        self.llm = LLMClient()

    async def classify(self, message: str) -> IntentClassificationResult:
        data = await self.llm.call(
            INTENT_CLASSIFICATION_PROMPT,
            message,
            context="Intent classification",
        )
        return IntentClassificationResult.model_validate(data)
