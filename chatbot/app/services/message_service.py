"""
Message service — processes chat messages through the agent pipeline.
"""
import json
import logging
from typing import Optional, Dict, Any, List, Union, Protocol

from ..agents.flow_agent import FlowAgent
from ..agents.flow_agent.models import FlowResult
from ..agents.title_agent import TitleAgent
from ..repository.conversation_repository import ConversationRepositoryProtocol
from ..repository.user_repository import UserRepositoryProtocol
from ..config.logger import ChatBotLogger

logger = logging.getLogger(__name__)

# Maximum number of previous messages to include as context
_MAX_HISTORY_MESSAGES = 10


class MessageServiceProtocol(Protocol):
    async def generate_conversation_title(self, user_message: str) -> str: ...
    async def process_chat_message(
        self,
        message: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]: ...


class MessageService:
    def __init__(
        self,
        conversation_repo: ConversationRepositoryProtocol,
        user_repo: UserRepositoryProtocol,
        flow_agent: Optional[FlowAgent] = None,
        title_agent: Optional[TitleAgent] = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._user_repo = user_repo
        self._flow_agent = flow_agent or FlowAgent()
        self._title_agent = title_agent or TitleAgent()

    def _get_user_first_name(self, user_id: Optional[Union[int, str]]) -> Optional[str]:
        """Fetch first_name from user_account for greeting personalization."""
        try:
            return self._user_repo.get_user_first_name(user_id)
        except Exception as exc:
            logger.warning(f"Could not load user first_name: {exc}")
            return None

    def _build_conversation_history(
        self,
        conversation_id: Optional[int],
    ) -> List[Dict[str, str]]:
        """
        Fetch most recent conversation messages and return multi-turn context.
        """
        if conversation_id is None:
            return []

        try:
            recent = self._conversation_repo.list_recent_messages(
                conversation_id=conversation_id,
                limit=_MAX_HISTORY_MESSAGES,
            )
            if not recent:
                return []

            history: List[Dict[str, str]] = []
            for msg in recent:
                role = "assistant" if msg.sender == "assistant" else "user"
                content = msg.content or ""

                if role == "assistant" and msg.response_data:
                    extras = []
                    if msg.response_data.get("intent"):
                        extras.append(f"[intent: {msg.response_data['intent']}]")
                    if msg.response_data.get("sql"):
                        extras.append(f"[sql used: {msg.response_data['sql']}]")
                    if extras:
                        content = f"{content}\n{'  '.join(extras)}"

                    if msg.response_data.get("candidates"):
                        toon_entries = []
                        for c in msg.response_data["candidates"][:10]:
                            toon_entries.append({
                                "id": c.get("id"),
                                "name": c.get("full_name"),
                                "position": c.get("applied_position"),
                                "experience": c.get("years_of_experience"),
                                "skills": c.get("tech_stack"),
                                "current_salary": c.get("current_salary"),
                                "expected_remote": c.get("expected_salary_remote"),
                                "expected_onsite": c.get("expected_salary_onsite"),
                            })
                        content += f"\n[retrieved_candidates: {json.dumps(toon_entries, default=str)}]"
                        cands = msg.response_data["candidates"]
                        if len(cands) == 1:
                            pc = cands[0]
                            content += f"\n[focus_candidate: {json.dumps({'id': pc.get('id'), 'name': pc.get('full_name')}, default=str)}]"
                        elif len(cands) > 1:
                            content += (
                                "\n[note: multiple candidates above; follow-ups with "
                                "'the first', 'the second', or a name should resolve to one row.]"
                            )

                    summ = msg.response_data.get("summary")
                    if summ and isinstance(summ, str) and summ.strip():
                        excerpt = summ.strip()[:800]
                        if len(summ) > 800:
                            excerpt += "..."
                        content += f"\n[assistant_summary_excerpt: {excerpt}]"

                    if msg.response_data.get("stats"):
                        content += f"\n[stats: {json.dumps(msg.response_data['stats'], default=str)}]"

                history.append({"role": role, "content": content})

            return history

        except Exception as exc:
            logger.warning(f"Could not load conversation history: {exc}")
            return []

    @staticmethod
    def _to_response_data(result: FlowResult) -> Dict[str, Any]:
        response_data: Dict[str, Any] = {
            "intent": result.intent,
            "summary": result.summary,
            "total_found": result.total_found,
            "sql": result.sql,
            "explanation": result.explanation,
        }
        if result.rows is not None:
            response_data["candidates"] = result.rows
        if result.stats is not None:
            response_data["stats"] = result.stats
        return response_data

    async def generate_conversation_title(self, user_message: str) -> str:
        """Generate a 2-4 word title for a conversation using the Title Agent."""
        return await self._title_agent.generate(user_message)

    async def process_chat_message(
        self,
        message: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the full agent pipeline.
        """
        conversation_history = self._build_conversation_history(conversation_id)
        user_first_name = self._get_user_first_name(user_id)

        chatbot_logger = ChatBotLogger(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        chatbot_logger.start_request()

        if conversation_history:
            chatbot_logger.log_section(
                "CONVERSATION CONTEXT",
                history_messages=len(conversation_history),
            )

        try:
            result = await self._flow_agent.process(
                message,
                self._conversation_repo.db,
                user_first_name=user_first_name,
                chatbot_logger=chatbot_logger,
                conversation_history=conversation_history,
            )
            chatbot_logger.end_request()
            return {
                "reply": result.reply,
                "response": self._to_response_data(result),
            }
        except Exception as exc:
            logger.error(f"Agent pipeline error: {exc}", exc_info=True)
            chatbot_logger.log_section("ERROR", error=str(exc))
            chatbot_logger.end_request()
            return {
                "reply": "I apologize, but I encountered an error processing your message. Please try again.",
                "response": None,
            }
