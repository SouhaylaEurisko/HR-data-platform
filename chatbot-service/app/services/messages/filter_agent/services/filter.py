"""
Filter service — LLM generates SQL, we execute, LLM summarises.
"""
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ....utils.llm_client import LLMClient
from ....utils.db_utils import execute_safe_query
from ..prompts import FILTER_SQL_PROMPT, FILTER_SUMMARY_PROMPT
from ..utils import rows_to_display, sanitize_rows

logger = logging.getLogger(__name__)


async def generate_filter_sql(llm: LLMClient, user_message: str) -> Dict[str, str]:
    """Ask LLM to produce a SELECT query for the user's filter request."""
    return await llm.call(
        FILTER_SQL_PROMPT,
        user_message,
        context="Filter SQL generation",
    )


async def summarise_results(
    llm: LLMClient,
    user_message: str,
    rows: List[Dict[str, Any]],
    total: int,
) -> Dict[str, str]:
    """Ask LLM to write a summary paragraph about the query results."""
    display = rows_to_display(rows)
    prompt_input = (
        f"User asked: {user_message}\n"
        f"Total candidates found: {total}\n\n"
        f"Results:\n{display}"
    )
    return await llm.call(
        FILTER_SUMMARY_PROMPT,
        prompt_input,
        context="Filter results summary",
        temperature=0.4,
    )
