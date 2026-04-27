"""
Combined filter + aggregation service.
"""
import logging
from typing import Any, Dict, List, Optional

from .prompts import FILTER_AGG_SQL_PROMPT, FILTER_AGG_SUMMARY_PROMPT
from .utils import rows_to_display, stats_to_display
from ..dtos import FilterAggregationSQLResult, FilterAggSummaryResult
from ...utils.pydantic_ai_client import (
    attach_sql_output_validator,
    build_agent,
    run_typed,
)

logger = logging.getLogger(__name__)

# Module-level typed agents — stateless, built once at import time.
_sql_agent = attach_sql_output_validator(
    build_agent(
        FilterAggregationSQLResult,
        FILTER_AGG_SQL_PROMPT,
        temperature=0.2,
    ),
    fields=("filter_sql", "aggregation_sql"),
)
_summary_agent = build_agent(
    FilterAggSummaryResult,
    FILTER_AGG_SUMMARY_PROMPT,
    temperature=0.4,
)


async def generate_filter_agg_sql(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> FilterAggregationSQLResult:
    """Ask LLM to produce both filter and aggregation SQL in a single call."""
    return await run_typed(
        _sql_agent,
        user_message,
        context="Filter+Aggregation SQL generation",
        conversation_history=conversation_history,
    )


async def summarise_filter_agg(
    user_message: str,
    rows: List[Dict[str, Any]],
    stats: List[Dict[str, Any]],
    total: int,
    *,
    stats_only: bool = False,
) -> FilterAggSummaryResult:
    """Ask LLM to summarise the combined filter + aggregation results."""
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
    return await run_typed(
        _summary_agent,
        prompt_input,
        context="Filter+Aggregation summary",
    )
