"""Intent Classifier Agent — pure-LLM intent routing."""

from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from .models import IntentClassificationResult
from ...config.logger import ChatBotLogger
from ...utils.pydantic_ai_client import PydanticAIClient


class IntentClassifierAgent:
    """Classifies user messages into one of the supported intents."""

    def __init__(
        self,
        agent: Agent[Any, IntentClassificationResult],
        ai_client: PydanticAIClient,
    ):
        self._agent = agent
        self._ai_client = ai_client

    async def classify(
        self,
        message: str,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> IntentClassificationResult:
        if chatbot_logger:
            chatbot_logger.log_section("INTENT CLASSIFIER", user_message=message)

        result = await self._ai_client.run_typed(
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
