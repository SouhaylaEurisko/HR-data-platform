"""
Filter + Aggregation Agent — entry point.
Runs both a filter query and an aggregation query, then summarises.
"""
import logging
from sqlalchemy.orm import Session

from .models import FilterAggregationResult
from .utils import sanitize_rows, sanitize_stats
from .services.filter_aggregation import generate_filter_agg_sql, summarise_filter_agg
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query

logger = logging.getLogger(__name__)


class FilterAggregationAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(self, message: str, db: Session) -> FilterAggregationResult:
        # 1. LLM generates both queries
        sql_result = await generate_filter_agg_sql(self.llm, message)
        filter_sql = sql_result["filter_sql"]
        agg_sql = sql_result["aggregation_sql"]
        explanation = sql_result.get("explanation", "")

        # 2. Execute filter query
        rows = []
        try:
            rows = execute_safe_query(db, filter_sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Filter query failed: {exc}")

        # 3. Execute aggregation query
        stats = []
        try:
            stats = execute_safe_query(db, agg_sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Aggregation query failed: {exc}")

        safe_rows = sanitize_rows(rows)
        safe_stats = sanitize_stats(stats)
        total = len(safe_rows)

        if total == 0 and not safe_stats:
            return FilterAggregationResult(
                filter_sql=filter_sql,
                aggregation_sql=agg_sql,
                explanation=explanation,
                rows=[],
                stats=[],
                total_found=0,
                summary="No matching candidates or statistics found.",
                reply="No candidates were found matching your criteria.",
            )

        # 4. LLM summarises
        summary_data = await summarise_filter_agg(
            self.llm, message, safe_rows, safe_stats, total
        )

        return FilterAggregationResult(
            filter_sql=filter_sql,
            aggregation_sql=agg_sql,
            explanation=explanation,
            rows=safe_rows,
            stats=safe_stats,
            total_found=total,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", f"Found {total} candidate(s) with statistics."),
        )
