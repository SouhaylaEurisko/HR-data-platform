"""
Aggregation service — LLM generates SQL with aggregation, we execute, LLM summarises.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ....utils.llm_client import LLMClient
from ....utils.db_utils import execute_safe_query
from ..prompts import AGGREGATION_SQL_PROMPT, AGGREGATION_SUMMARY_PROMPT
from ..utils import stats_to_display, sanitize_stats

logger = logging.getLogger(__name__)


async def generate_aggregation_sql(
    llm: LLMClient,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    """Ask LLM to produce a SELECT query with aggregation functions."""
    return await llm.call(
        AGGREGATION_SQL_PROMPT,
        user_message,
        context="Aggregation SQL generation",
        conversation_history=conversation_history,
    )


async def summarise_stats(
    llm: LLMClient,
    user_message: str,
    stats: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Ask LLM to write a summary paragraph about the aggregation results."""
    display = stats_to_display(stats)
    prompt_input = (
        f"User asked: {user_message}\n\n"
        f"Aggregation results:\n{display}"
    )
    return await llm.call(
        AGGREGATION_SUMMARY_PROMPT,
        prompt_input,
        context="Aggregation results summary",
        temperature=0.4,
    )
