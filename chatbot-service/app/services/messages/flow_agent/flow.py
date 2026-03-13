"""
Flow Agent — the orchestrator.

1. Classify intent (LLM)
2. Route to the correct agent
3. Return a unified FlowResult
"""
import logging
from sqlalchemy.orm import Session

from .models import FlowResult
from ..intent_classifier_agent import IntentClassifierAgent
from ..chit_chat_agent import ChitChatAgent
from ..filter_agent import FilterAgent
from ..aggregation_agent import AggregationAgent
from ..filter_aggregation_agent import FilterAggregationAgent

logger = logging.getLogger(__name__)


class FlowAgent:
    """Coordinates the full message-processing pipeline."""

    def __init__(self):
        self.classifier = IntentClassifierAgent()
        self.chitchat = ChitChatAgent()
        self.filter = FilterAgent()
        self.aggregation = AggregationAgent()
        self.filter_agg = FilterAggregationAgent()

    async def process(self, message: str, db: Session) -> FlowResult:
        """
        Process a user message end-to-end.

        Args:
            message: Raw user text.
            db:      SQLAlchemy session for query execution.

        Returns:
            FlowResult with reply, optional data rows, stats, summary.
        """
        # ── 1. Classify intent ──
        classification = await self.classifier.classify(message)
        intent = classification.intent
        logger.info(f"Intent: {intent} (confidence: {classification.confidence})")

        # ── 2. Route to agent ──

        if intent == "chitchat":
            result = await self.chitchat.respond(message)
            return FlowResult(intent=intent, reply=result.reply)

        if intent == "filter":
            result = await self.filter.process(message, db)
            return FlowResult(
                intent=intent,
                reply=result.reply,
                summary=result.summary,
                rows=result.rows,
                total_found=result.total_found,
                sql=result.sql,
                explanation=result.explanation,
            )

        if intent == "aggregation":
            result = await self.aggregation.process(message, db)
            return FlowResult(
                intent=intent,
                reply=result.reply,
                summary=result.summary,
                stats=result.stats,
                sql=result.sql,
                explanation=result.explanation,
            )

        if intent == "filter_and_aggregation":
            result = await self.filter_agg.process(message, db)
            return FlowResult(
                intent=intent,
                reply=result.reply,
                summary=result.summary,
                rows=result.rows,
                stats=result.stats,
                total_found=result.total_found,
                sql=result.filter_sql,
                explanation=result.explanation,
            )

        # Fallback — treat unknown intents as chitchat
        logger.warning(f"Unknown intent '{intent}', falling back to chitchat")
        result = await self.chitchat.respond(message)
        return FlowResult(intent="chitchat", reply=result.reply)
