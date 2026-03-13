"""
Combined filter + aggregation service.
"""
import logging
from typing import Any, Dict, List

from ....utils.llm_client import LLMClient
from ..prompts import FILTER_AGG_SQL_PROMPT, FILTER_AGG_SUMMARY_PROMPT
from ..utils import rows_to_display, stats_to_display

logger = logging.getLogger(__name__)


async def generate_filter_agg_sql(llm: LLMClient, user_message: str) -> Dict[str, str]:
    return await llm.call(
        FILTER_AGG_SQL_PROMPT,
        user_message,
        context="Filter+Aggregation SQL generation",
    )


async def summarise_filter_agg(
    llm: LLMClient,
    user_message: str,
    rows: List[Dict[str, Any]],
    stats: List[Dict[str, Any]],
    total: int,
) -> Dict[str, str]:
    row_display = rows_to_display(rows)
    stat_display = stats_to_display(stats)
    prompt_input = (
        f"User asked: {user_message}\n"
        f"Total candidates found: {total}\n\n"
        f"Sample candidates:\n{row_display}\n\n"
        f"Aggregation statistics:\n{stat_display}"
    )
    return await llm.call(
        FILTER_AGG_SUMMARY_PROMPT,
        prompt_input,
        context="Filter+Aggregation summary",
        temperature=0.4,
    )
