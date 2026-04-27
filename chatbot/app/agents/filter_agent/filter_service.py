"""
Filter service — LLM generates SQL, we execute, LLM summarises.
"""
import logging
from typing import Any, Dict, List, Optional

from .prompts import FILTER_SQL_PROMPT, FILTER_SUMMARY_PROMPT
from .utils import rows_to_display
from ..dtos import FilterSummaryResult, SQLGenerationResult
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
        FILTER_SQL_PROMPT,
        temperature=0.2,
    ),
)
_summary_agent = build_agent(
    FilterSummaryResult,
    FILTER_SUMMARY_PROMPT,
    temperature=0.4,
)


async def generate_filter_sql(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> SQLGenerationResult:
    """Ask LLM to produce a SELECT query for the user's filter request."""
    return await run_typed(
        _sql_agent,
        user_message,
        context="Filter SQL generation",
        conversation_history=conversation_history,
    )


async def summarise_results(
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
    return await run_typed(
        _summary_agent,
        prompt_input,
        context="Filter results summary",
    )
