"""Aggregation service — LLM generates SQL and summarizes resulting stats."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from .utils import stats_to_display
from ..dtos import AggregationSummaryResult, SQLGenerationResult
from ...utils.pydantic_ai_client import PydanticAIClient


class AggregationService:
    """Orchestrates typed LLM calls for aggregation SQL and summaries."""

    def __init__(
        self,
        sql_agent: Agent[Any, SQLGenerationResult],
        summary_agent: Agent[Any, AggregationSummaryResult],
        ai_client: PydanticAIClient,
    ) -> None:
        self._sql_agent = sql_agent
        self._summary_agent = summary_agent
        self._ai_client = ai_client

    async def generate_aggregation_sql(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> SQLGenerationResult:
        """Ask LLM to produce a SELECT query with aggregation functions."""
        return await self._ai_client.run_typed(
            self._sql_agent,
            user_message,
            context="Aggregation SQL generation",
            conversation_history=conversation_history,
        )

    async def summarise_stats(
        self,
        user_message: str,
        stats: List[Dict[str, Any]],
    ) -> AggregationSummaryResult:
        """Ask LLM to write a summary paragraph about aggregation results."""
        display = stats_to_display(stats)
        prompt_input = (
            f"User asked: {user_message}\n\n"
            f"Aggregation results:\n{display}"
        )
        return await self._ai_client.run_typed(
            self._summary_agent,
            prompt_input,
            context="Aggregation results summary",
        )
