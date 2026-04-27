"""Chit Chat Agent — handles greetings, thanks, off-topic."""
from typing import Dict, List, Optional

from .models import ChitChatResult
from .prompts import CHITCHAT_PROMPT
from ...utils.pydantic_ai_client import build_agent, run_typed
from ...config.logger import ChatBotLogger


class ChitChatAgent:
    def __init__(self):
        self._agent = build_agent(
            ChitChatResult,
            CHITCHAT_PROMPT,
            temperature=0.88,
        )

    async def respond(
        self,
        message: str,
        user_first_name: Optional[str] = None,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChitChatResult:
        if chatbot_logger:
            chatbot_logger.log_section("CHIT CHAT", user_message=message)

        # Pass first-name context so greetings can be personalized.
        llm_input = (
            f"USER_FIRST_NAME: {user_first_name or ''}\n"
            f"USER_MESSAGE: {message}"
        )

        result = await run_typed(
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
