"""
Aggregation Agent — entry point.
1. LLM → aggregation SQL   2. Execute SQL   3. LLM → Summary
"""
import logging
from sqlalchemy.orm import Session

from .models import AggregationAgentResult
from .utils import sanitize_stats
from .services.aggregation import generate_aggregation_sql, summarise_stats
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query

logger = logging.getLogger(__name__)


class AggregationAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(self, message: str, db: Session) -> AggregationAgentResult:
        # 1. LLM generates aggregation SQL
        sql_result = await generate_aggregation_sql(self.llm, message)
        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")

        # 2. Execute query
        try:
            rows = execute_safe_query(db, sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Aggregation query failed: {exc}")
            return AggregationAgentResult(
                sql=sql,
                explanation=explanation,
                stats=[],
                summary="I could not compute the statistics. Please rephrase your request.",
                reply="Sorry, I had trouble processing that. Could you rephrase?",
            )

        safe_stats = sanitize_stats(rows)

        # 3. LLM summarises
        if not safe_stats:
            return AggregationAgentResult(
                sql=sql,
                explanation=explanation,
                stats=[],
                summary="No data available for the requested statistics.",
                reply="No data was found to compute the requested statistics.",
            )

        summary_data = await summarise_stats(self.llm, message, safe_stats)

        return AggregationAgentResult(
            sql=sql,
            explanation=explanation,
            stats=safe_stats,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", "Here are the statistics."),
        )
