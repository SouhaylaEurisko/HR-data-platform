"""Chit Chat Agent — handles greetings, thanks, off-topic."""
from typing import Dict, List, Optional

from .models import ChitChatResult
from .prompts import CHITCHAT_PROMPT
from ...utils.llm_client import LLMClient
from ....config.logger import ChatBotLogger


class ChitChatAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def respond(
        self,
        message: str,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChitChatResult:
        # Log input
        if chatbot_logger:
            chatbot_logger.log_section("CHIT CHAT", user_message=message)

        data = await self.llm.call(
            CHITCHAT_PROMPT,
            message,
            context="Chit-chat",
            temperature=0.88,
            conversation_history=conversation_history,
        )
        result = ChitChatResult.model_validate(data)

        # Log output
        if chatbot_logger:
            chatbot_logger.log_section(
                "CHIT CHAT",
                user_message=message,
                assistant_response=result.reply,
            )

        return result
