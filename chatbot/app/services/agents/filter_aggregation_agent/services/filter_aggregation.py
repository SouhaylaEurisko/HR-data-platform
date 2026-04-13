"""
Combined filter + aggregation service.
"""
import logging
from typing import Any, Dict, List, Optional

from ....utils.llm_client import LLMClient
from ..prompts import FILTER_AGG_SQL_PROMPT, FILTER_AGG_SUMMARY_PROMPT
from ..utils import rows_to_display, stats_to_display

logger = logging.getLogger(__name__)


async def generate_filter_agg_sql(
    llm: LLMClient,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    return await llm.call(
        FILTER_AGG_SQL_PROMPT,
        user_message,
        context="Filter+Aggregation SQL generation",
        conversation_history=conversation_history,
    )


async def summarise_filter_agg(
    llm: LLMClient,
    user_message: str,
    rows: List[Dict[str, Any]],
    stats: List[Dict[str, Any]],
    total: int,
    *,
    stats_only: bool = False,
) -> Dict[str, str]:
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
    return await llm.call(
        FILTER_AGG_SUMMARY_PROMPT,
        prompt_input,
        context="Filter+Aggregation summary",
        temperature=0.4,
    )
