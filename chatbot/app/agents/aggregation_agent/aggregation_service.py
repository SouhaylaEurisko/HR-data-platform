"""
Aggregation service — LLM generates SQL with aggregation, we execute, LLM summarises.
"""
import logging
from typing import Any, Dict, List, Optional

from .prompts import AGGREGATION_SQL_PROMPT, AGGREGATION_SUMMARY_PROMPT
from .utils import stats_to_display
from ..dtos import AggregationSummaryResult, SQLGenerationResult
from ...utils.pydantic_ai_client import (
    attach_sql_output_validator,
    build_agent,
    run_typed,
)

logger = logging.getLogger(__name__)

# Module-level typed agents — stateless, built once at import time.
_sql_agent = attach_sql_output_validator(
    build_agent(
        SQLGenerationResult,
        AGGREGATION_SQL_PROMPT,
        temperature=0.2,
    ),
)
_summary_agent = build_agent(
    AggregationSummaryResult,
    AGGREGATION_SUMMARY_PROMPT,
    temperature=0.4,
)


async def generate_aggregation_sql(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> SQLGenerationResult:
    """Ask LLM to produce a SELECT query with aggregation functions."""
    return await run_typed(
        _sql_agent,
        user_message,
        context="Aggregation SQL generation",
        conversation_history=conversation_history,
    )


async def summarise_stats(
    user_message: str,
    stats: List[Dict[str, Any]],
) -> AggregationSummaryResult:
    """Ask LLM to write a summary paragraph about the aggregation results."""
    display = stats_to_display(stats)
    prompt_input = (
        f"User asked: {user_message}\n\n"
        f"Aggregation results:\n{display}"
    )
    return await run_typed(
        _summary_agent,
        prompt_input,
        context="Aggregation results summary",
    )
