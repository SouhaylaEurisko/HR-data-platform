"""Intent Classifier Agent — pure-LLM intent routing."""
from typing import Dict, List, Optional

from .models import IntentClassificationResult
from .prompts import INTENT_CLASSIFICATION_PROMPT
from ...utils.pydantic_ai_client import build_agent, run_typed
from ...config.logger import ChatBotLogger


class IntentClassifierAgent:
    """Classifies user messages into one of the supported intents."""

    def __init__(self):
        self._agent = build_agent(
            IntentClassificationResult,
            INTENT_CLASSIFICATION_PROMPT,
            temperature=0.2,
        )

    async def classify(
        self,
        message: str,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> IntentClassificationResult:
        if chatbot_logger:
            chatbot_logger.log_section("INTENT CLASSIFIER", user_message=message)

        result = await run_typed(
            self._agent,
            message,
            context="Intent classification",
            conversation_history=conversation_history,
        )

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
