"""Combined filter + aggregation service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from .utils import rows_to_display, stats_to_display
from ..dtos import FilterAggregationSQLResult, FilterAggSummaryResult
from ...utils.pydantic_ai_client import PydanticAIClient


class FilterAggregationService:
    """Orchestrates typed LLM calls for combined filter + aggregation operations."""

    def __init__(
        self,
        sql_agent: Agent[Any, FilterAggregationSQLResult],
        summary_agent: Agent[Any, FilterAggSummaryResult],
        ai_client: PydanticAIClient,
    ) -> None:
        self._sql_agent = sql_agent
        self._summary_agent = summary_agent
        self._ai_client = ai_client

    async def generate_filter_agg_sql(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> FilterAggregationSQLResult:
        """Ask LLM to produce both filter and aggregation SQL in one call."""
        return await self._ai_client.run_typed(
            self._sql_agent,
            user_message,
            context="Filter+Aggregation SQL generation",
            conversation_history=conversation_history,
        )

    async def summarise_filter_agg(
        self,
        user_message: str,
        rows: List[Dict[str, Any]],
        stats: List[Dict[str, Any]],
        total: int,
        *,
        stats_only: bool = False,
    ) -> FilterAggSummaryResult:
        """Ask LLM to summarize combined filter and aggregation results."""
        stat_display = stats_to_display(stats)
        if stats_only:
            prompt_input = (
                f"User asked: {user_message}\n"
                f"Total candidates in the filtered set (from aggregation): {total}\n\n"
                "No per-candidate rows were loaded; the user asked for counts/statistics only.\n\n"
                f"Aggregation statistics:\n{stat_display}\n\n"
                "IMPORTANT: Do not name or list individual candidates. "
                "Answer using only counts and aggregation metrics. "
                "Keep summary to 1–3 sentences; reply one short sentence."
            )
        else:
            row_display = rows_to_display(rows)
            prompt_input = (
                f"User asked: {user_message}\n"
                f"Total candidates found: {total}\n\n"
                f"Sample candidates:\n{row_display}\n\n"
                f"Aggregation statistics:\n{stat_display}"
            )
        return await self._ai_client.run_typed(
            self._summary_agent,
            prompt_input,
            context="Filter+Aggregation summary",
        )
