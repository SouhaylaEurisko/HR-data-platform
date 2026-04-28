"""Filter service — LLM generates SQL, we execute, then LLM summarizes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from .utils import rows_to_display
from ..dtos import FilterSummaryResult, SQLGenerationResult
from ...utils.pydantic_ai_client import PydanticAIClient


class FilterService:
    """Orchestrates typed LLM calls for filter SQL and response summaries."""

    def __init__(
        self,
        sql_agent: Agent[Any, SQLGenerationResult],
        summary_agent: Agent[Any, FilterSummaryResult],
        ai_client: PydanticAIClient,
    ) -> None:
        self._sql_agent = sql_agent
        self._summary_agent = summary_agent
        self._ai_client = ai_client

    async def generate_filter_sql(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> SQLGenerationResult:
        """Ask LLM to produce a SELECT query for the user's filter request."""
        return await self._ai_client.run_typed(
            self._sql_agent,
            user_message,
            context="Filter SQL generation",
            conversation_history=conversation_history,
        )

    async def summarise_results(
        self,
        user_message: str,
        rows: List[Dict[str, Any]],
        total: int,
    ) -> FilterSummaryResult:
        """Ask LLM to write a summary paragraph about the query results."""
        display = rows_to_display(rows)
        prompt_input = (
            f"User asked: {user_message}\n"
            f"Total candidates found: {total}\n\n"
            f"Results:\n{display}"
        )
        return await self._ai_client.run_typed(
            self._summary_agent,
            prompt_input,
            context="Filter results summary",
        )
