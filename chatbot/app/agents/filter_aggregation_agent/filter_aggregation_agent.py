"""
Filter + Aggregation Agent — entry point.
Runs both a filter query and an aggregation query, then summarises.
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .models import FilterAggregationResult
from .intent_helpers import is_count_only_query, total_candidates_from_stats
from .utils import sanitize_rows, sanitize_stats
from ..filter_agent.utils import filter_empty_rows, resort_by_salary
from .services.filter_aggregation import generate_filter_agg_sql, summarise_filter_agg
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query, execute_salary_aware_query, fetch_salary_stats_for_query, fetch_experience_stats_for_query
from ...config.logger import ChatBotLogger

# Re-use the correction logic from the aggregation agent
from ..aggregation_agent.aggregation_agent import _apply_salary_correction, _apply_experience_correction

logger = logging.getLogger(__name__)


class FilterAggregationAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> FilterAggregationResult:
        # 1. LLM generates both queries
        sql_result = await generate_filter_agg_sql(self.llm, message, conversation_history=conversation_history)
        filter_sql = sql_result["filter_sql"]
        agg_sql = sql_result["aggregation_sql"]
        explanation = sql_result.get("explanation", "")

        count_only = is_count_only_query(message)

        # Log SQL generation
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER + AGGREGATION - SQL GENERATION",
                user_query=message,
                filter_sql=filter_sql,
                aggregation_sql=agg_sql,
                explanation=explanation,
                count_only_question=count_only,
            )

        # 2. Execute filter query (salary-aware), unless user only asked for a count/total
        rows = []
        if count_only:
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER + AGGREGATION - FILTER EXECUTION",
                    status="SKIPPED",
                    reason="Count-only question; aggregation supplies totals without sample rows",
                )
        else:
            try:
                rows, salary_corrected = execute_salary_aware_query(db, filter_sql)
                if salary_corrected and chatbot_logger:
                    chatbot_logger.log_section(
                        "FILTER + AGGREGATION - SALARY FILTER CORRECTION",
                        status="APPLIED",
                        rows_after_correction=len(rows),
                    )
            except (ValueError, RuntimeError) as exc:
                logger.error(f"Filter query failed: {exc}")
                if chatbot_logger:
                    chatbot_logger.log_section(
                        "FILTER + AGGREGATION - FILTER EXECUTION",
                        status="FAILED",
                        error=str(exc),
                    )

        # 3. Execute aggregation query
        stats = []
        try:
            stats = execute_safe_query(db, agg_sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Aggregation query failed: {exc}")
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER + AGGREGATION - AGGREGATION EXECUTION",
                    status="FAILED",
                    error=str(exc),
                )

        safe_rows = sanitize_rows(rows)
        safe_stats = sanitize_stats(stats)

        # Filter out empty/corrupt rows and re-sort correctly
        filter_upper = filter_sql.upper()
        if "ORDER BY YEARS_OF_EXPERIENCE" in filter_upper:
            safe_rows = filter_empty_rows(safe_rows, required_field="years_of_experience")
        elif "ORDER BY CURRENT_SALARY" in filter_upper:
            # Do not drop NULL current_salary — many valid candidates lack it; stats still use FILTER on aggregates
            safe_rows = filter_empty_rows(safe_rows, required_field=None)
            tail = filter_upper.split("ORDER BY CURRENT_SALARY", 1)[1]
            descending = "DESC" in tail.split("LIMIT")[0]
            safe_rows = resort_by_salary(safe_rows, descending=descending)

        stat_total = total_candidates_from_stats(safe_stats)
        if count_only:
            total = stat_total if stat_total is not None else 0
        else:
            total = len(safe_rows)

        # Log raw data from DB (before corrections)
        if chatbot_logger:
            chatbot_logger.log_db_rows("FILTER + AGGREGATION - DB ROWS RETRIEVED", safe_rows)
            chatbot_logger.log_db_stats("FILTER + AGGREGATION - RAW DB STATS", safe_stats)

        # 3b. Correct salary statistics
        salary_stats = fetch_salary_stats_for_query(db, agg_sql)
        if salary_stats:
            safe_stats = _apply_salary_correction(safe_stats, salary_stats)
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER + AGGREGATION - SALARY CORRECTION",
                    status="APPLIED",
                    parsed_count=salary_stats.get("count", 0),
                    min_salary=salary_stats.get("min_salary"),
                    max_salary=salary_stats.get("max_salary"),
                    avg_min_salary=salary_stats.get("avg_min_salary"),
                    avg_max_salary=salary_stats.get("avg_max_salary"),
                )

        # 3c. Correct experience statistics (exclude corrupt values > 50)
        exp_stats = fetch_experience_stats_for_query(db, agg_sql)
        if exp_stats:
            safe_stats = _apply_experience_correction(safe_stats, exp_stats)
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER + AGGREGATION - EXPERIENCE CORRECTION",
                    status="APPLIED",
                    valid_count=exp_stats.get("count", 0),
                    min_experience=exp_stats.get("min_experience"),
                    max_experience=exp_stats.get("max_experience"),
                    avg_experience=exp_stats.get("avg_experience"),
                )

        # Log corrected stats + query execution
        if chatbot_logger:
            chatbot_logger.log_db_stats("FILTER + AGGREGATION - CORRECTED STATS (sent to LLM)", safe_stats)
            chatbot_logger.log_section(
                "FILTER + AGGREGATION - QUERY EXECUTION",
                filter_rows_found=len(safe_rows),
                aggregation_stats_rows=len(safe_stats),
            )

        if not safe_stats and not safe_rows:
            result = FilterAggregationResult(
                filter_sql=filter_sql,
                aggregation_sql=agg_sql,
                explanation=explanation,
                rows=[],
                stats=[],
                total_found=0,
                summary="No matching candidates or statistics found.",
                reply="No candidates were found matching your criteria.",
            )
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER + AGGREGATION - RESULT",
                    total_found=0,
                    summary=result.summary,
                    reply=result.reply,
                )
            return result

        # 4. LLM summarises
        summary_data = await summarise_filter_agg(
            self.llm,
            message,
            safe_rows,
            safe_stats,
            total,
            stats_only=count_only,
        )

        result = FilterAggregationResult(
            filter_sql=filter_sql,
            aggregation_sql=agg_sql,
            explanation=explanation,
            rows=safe_rows,
            stats=safe_stats,
            total_found=total,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", f"Found {total} candidate(s) with statistics."),
        )

        # Log final result
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER + AGGREGATION - RESULT",
                total_found=total,
                stats_count=len(safe_stats),
                summary=result.summary,
                reply=result.reply,
            )

        return result
