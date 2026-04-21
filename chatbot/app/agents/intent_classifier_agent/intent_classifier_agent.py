"""Intent Classifier Agent — pure-LLM intent routing."""
from typing import Dict, List, Optional

from .models import IntentClassificationResult
from .prompts import INTENT_CLASSIFICATION_PROMPT
from ...utils.llm_client import LLMClient
from ...config.logger import ChatBotLogger


class IntentClassifierAgent:
    """Classifies user messages into one of the supported intents."""

    def __init__(self):
        self.llm = LLMClient()

    async def classify(
        self,
        message: str,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> IntentClassificationResult:
        # Log input
        if chatbot_logger:
            chatbot_logger.log_section("INTENT CLASSIFIER", user_message=message)

        data = await self.llm.call(
            INTENT_CLASSIFICATION_PROMPT,
            message,
            context="Intent classification",
            conversation_history=conversation_history,
        )
        result = IntentClassificationResult.model_validate(data)

        # Log classification result
        if chatbot_logger:
            chatbot_logger.log_section(
                "INTENT CLASSIFIER",
                user_message=message,
                classification_result={
                    "Intent": result.intent,
                    "Confidence": result.confidence,
                    "Reasoning": result.reasoning,
                },
            )

        return result
