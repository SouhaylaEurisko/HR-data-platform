"""
Message service — processes chat messages through the agent pipeline.
"""
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from ..services.messages.flow_agent import FlowAgent
from ..services.messages.title_agent import TitleAgent
from ..services.conversation_service import (
    create_conversation,
    get_conversation_by_id,
    add_message_to_conversation,
    update_conversation_title,
)

logger = logging.getLogger(__name__)

# Singleton-ish agents (stateless, safe to reuse)
_flow_agent = FlowAgent()
_title_agent = TitleAgent()


async def generate_conversation_title(user_message: str) -> str:
    """Generate a 2-4 word title for a conversation using the Title Agent."""
    return await _title_agent.generate(user_message)


async def process_chat_message(
    message: str,
    conversation_id: Optional[int] = None,
    db: Session = None,
) -> Dict[str, Any]:
    """
    Process a user message through the full agent pipeline.

    Flow:
      1. Intent Classifier classifies the message.
      2. Flow Agent routes to the correct agent.
      3. Agent processes (possibly generating SQL, querying DB, summarising).
      4. Returns unified result dict.

    Args:
        message:          User's text.
        conversation_id:  Optional conversation ID (for context).
        db:               SQLAlchemy session.

    Returns:
        Dict with keys: reply, response (full structured data).
    """
    if db is None:
        logger.warning("No DB session — agents that need SQL will fail gracefully.")

    try:
        result = await _flow_agent.process(message, db)

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

        return {
            "reply": result.reply,
            "response": response_data,
        }

    except Exception as exc:
        logger.error(f"Agent pipeline error: {exc}", exc_info=True)
        return {
            "reply": "I apologize, but I encountered an error processing your message. Please try again.",
            "response": None,
        }
