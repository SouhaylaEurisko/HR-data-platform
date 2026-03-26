"""
Message service — processes chat messages through the agent pipeline.
"""
import json
import logging
from typing import Optional, Dict, Any, List, Union

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..services.messages.flow_agent import FlowAgent
from ..services.messages.title_agent import TitleAgent
from ..services.conversation_service import (
    create_conversation,
    get_conversation_by_id,
    add_message_to_conversation,
    update_conversation_title,
)
from ..config.logger import ChatBotLogger

logger = logging.getLogger(__name__)

# Singleton-ish agents (stateless, safe to reuse)
_flow_agent = FlowAgent()
_title_agent = TitleAgent()

# Maximum number of previous messages to include as context
_MAX_HISTORY_MESSAGES = 10


def _get_user_first_name(db: Session, user_id: Optional[Union[int, str]]) -> Optional[str]:
    """Fetch first_name from user_account for greeting personalization."""
    if db is None or user_id is None:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None

    try:
        row = db.execute(
            text("SELECT first_name FROM user_account WHERE id = :uid LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not row:
            return None
        first = (row.get("first_name") or "").strip()
        return first or None
    except Exception as exc:
        logger.warning(f"Could not load user first_name: {exc}")
        return None


def _build_conversation_history(
    db: Session,
    conversation_id: Optional[int],
) -> List[Dict[str, str]]:
    """
    Fetch the most recent messages from a conversation and return them
    as a list of ``{"role": ..., "content": ...}`` dicts suitable for
    the OpenAI multi-turn messages API.

    Only the last ``_MAX_HISTORY_MESSAGES`` messages are included to keep
    token usage reasonable.
    """
    if db is None or conversation_id is None:
        return []

    try:
        conversation = get_conversation_by_id(db, conversation_id)
        if conversation is None or not conversation.messages:
            return []

        # conversation.messages is ordered by created_at ASC (see model)
        recent = conversation.messages[-_MAX_HISTORY_MESSAGES:]

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

                # Append condensed candidate data so follow-up questions
                # (pronouns, "that candidate", salary/skills) keep the same person in scope.
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
                        excerpt += "…"
                    content += f"\n[assistant_summary_excerpt: {excerpt}]"

                if msg.response_data.get("stats"):
                    content += f"\n[stats: {json.dumps(msg.response_data['stats'], default=str)}]"

            history.append({"role": role, "content": content})

        return history

    except Exception as exc:
        logger.warning(f"Could not load conversation history: {exc}")
        return []


async def generate_conversation_title(user_message: str) -> str:
    """Generate a 2-4 word title for a conversation using the Title Agent."""
    return await _title_agent.generate(user_message)


async def process_chat_message(
    message: str,
    conversation_id: Optional[int] = None,
    db: Session = None,
    user_id: Optional[Union[int, str]] = None,
) -> Dict[str, Any]:
    """
    Process a user message through the full agent pipeline.

    Flow:
      1. Load conversation history for context.
      2. Intent Classifier classifies the message (with history).
      3. Flow Agent routes to the correct agent (with history).
      4. Agent processes (possibly generating SQL, querying DB, summarising).
      5. Returns unified result dict.

    Args:
        message:          User's text.
        conversation_id:  Optional conversation ID (for context).
        db:               SQLAlchemy session.
        user_id:          Optional user ID (for logging).

    Returns:
        Dict with keys: reply, response (full structured data).
    """
    if db is None:
        logger.warning("No DB session — agents that need SQL will fail gracefully.")

    # ── Build conversation history for multi-turn context ──
    conversation_history = _build_conversation_history(db, conversation_id)
    user_first_name = _get_user_first_name(db, user_id)

    # ── Create per-request chatbot logger ──
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
        result = await _flow_agent.process(
            message,
            db,
            user_first_name=user_first_name,
            chatbot_logger=chatbot_logger,
            conversation_history=conversation_history,
        )

        # Build the response data dict (stored in response_data column)
        response_data = {
            "intent": result.intent,
            "summary": result.summary,
            "total_found": result.total_found,
            "sql": result.sql,
            "explanation": result.explanation,
        }

        # Include rows if present (filter / filter_and_aggregation)
        if result.rows is not None:
            response_data["candidates"] = result.rows

        # Include stats if present (aggregation / filter_and_aggregation)
        if result.stats is not None:
            response_data["stats"] = result.stats

        chatbot_logger.end_request()

        return {
            "reply": result.reply,
            "response": response_data,
        }

    except Exception as exc:
        logger.error(f"Agent pipeline error: {exc}", exc_info=True)
        chatbot_logger.log_section("ERROR", error=str(exc))
        chatbot_logger.end_request()
        return {
            "reply": "I apologize, but I encountered an error processing your message. Please try again.",
            "response": None,
        }
