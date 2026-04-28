"""Chit Chat Agent — handles greetings, thanks, and off-topic replies."""

from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from .models import ChitChatResult
from ...config.logger import ChatBotLogger
from ...utils.pydantic_ai_client import PydanticAIClient


class ChitChatAgent:
    def __init__(
        self,
        agent: Agent[Any, ChitChatResult],
        ai_client: PydanticAIClient,
    ):
        self._agent = agent
        self._ai_client = ai_client

    async def respond(
        self,
        message: str,
        user_first_name: Optional[str] = None,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChitChatResult:
        if chatbot_logger:
            chatbot_logger.log_section("CHIT CHAT", user_message=message)

        llm_input = (
            f"USER_FIRST_NAME: {user_first_name or ''}\n"
            f"USER_MESSAGE: {message}"
        )

        result = await self._ai_client.run_typed(
            self._agent,
            llm_input,
            context="Chit-chat",
            conversation_history=conversation_history,
        )

        if chatbot_logger:
            chatbot_logger.log_section(
                "CHIT CHAT",
                user_message=message,
                assistant_response=result.reply,
            )

        return result
