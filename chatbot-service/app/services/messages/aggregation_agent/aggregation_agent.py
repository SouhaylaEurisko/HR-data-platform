"""
Aggregation Agent — entry point.
1. LLM → aggregation SQL   2. Execute SQL   3. Correct salary stats   4. LLM → Summary
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .models import AggregationAgentResult
from .utils import sanitize_stats
from .services.aggregation import generate_aggregation_sql, summarise_stats
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query, fetch_salary_stats_for_query, fetch_experience_stats_for_query
from ....config.logger import ChatBotLogger

logger = logging.getLogger(__name__)


def _apply_salary_correction(
    stats: List[Dict],
    salary_stats: Dict,
) -> List[Dict]:
    """
    Replace unreliable salary aggregation values in *stats* with the
    correctly parsed numbers from *salary_stats*.

    The LLM-generated SQL may produce aggregation values that need
    correction.  ``salary_stats`` provides verified salary numbers.
    """
    if not stats or not salary_stats:
        return stats

    # Map of SQL-column-name patterns → corrected value
    corrections = {
        "max_current_salary": salary_stats.get("max_salary"),
        "min_current_salary": salary_stats.get("min_salary"),
        "avg_current_salary": salary_stats.get("avg_salary"),
        "max_salary": salary_stats.get("max_salary"),
        "min_salary": salary_stats.get("min_salary"),
        "avg_salary": salary_stats.get("avg_salary"),
    }

    corrected = []
    for row in stats:
        new_row = dict(row)
        for key in new_row:
            lk = key.lower()
            for pattern, correct_val in corrections.items():
                if pattern in lk and correct_val is not None:
                    new_row[key] = correct_val
                    break
        corrected.append(new_row)
    return corrected


def _apply_experience_correction(
    stats: List[Dict],
    exp_stats: Dict,
) -> List[Dict]:
    """
    Replace unreliable years_of_experience aggregation values in *stats*
    with correctly bounded numbers from *exp_stats*.
    """
    if not stats or not exp_stats:
        return stats

    corrections = {
        "max_years_of_experience": exp_stats.get("max_experience"),
        "min_years_of_experience": exp_stats.get("min_experience"),
        "avg_years_of_experience": exp_stats.get("avg_experience"),
        "max_experience": exp_stats.get("max_experience"),
        "min_experience": exp_stats.get("min_experience"),
        "avg_experience": exp_stats.get("avg_experience"),
    }

    corrected = []
    for row in stats:
        new_row = dict(row)
        for key in new_row:
            lk = key.lower()
            for pattern, correct_val in corrections.items():
                if pattern in lk and correct_val is not None:
                    new_row[key] = correct_val
                    break
        corrected.append(new_row)
    return corrected


class AggregationAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AggregationAgentResult:
        # 1. LLM generates aggregation SQL
        sql_result = await generate_aggregation_sql(self.llm, message, conversation_history=conversation_history)
        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")

        # Log SQL generation
        if chatbot_logger:
            chatbot_logger.log_section(
                "AGGREGATION - SQL GENERATION",
                user_query=message,
                generated_sql=sql,
                explanation=explanation,
            )

        # 2. Execute query
        try:
            rows = execute_safe_query(db, sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Aggregation query failed: {exc}")
            if chatbot_logger:
                chatbot_logger.log_section(
                    "AGGREGATION - QUERY EXECUTION",
                    status="FAILED",
                    error=str(exc),
                )
            return AggregationAgentResult(
                sql=sql,
                explanation=explanation,
                stats=[],
                summary="I could not compute the statistics. Please rephrase your request.",
                reply="Sorry, I had trouble processing that. Could you rephrase?",
            )

        safe_stats = sanitize_stats(rows)

        # Log raw stats from DB (before corrections)
        if chatbot_logger:
            chatbot_logger.log_db_stats("AGGREGATION - RAW DB STATS", safe_stats)

        # 2b. Correct salary statistics
        salary_stats = fetch_salary_stats_for_query(db, sql)
        if salary_stats:
            safe_stats = _apply_salary_correction(safe_stats, salary_stats)
            if chatbot_logger:
                chatbot_logger.log_section(
                    "AGGREGATION - SALARY CORRECTION",
                    status="APPLIED",
                    parsed_count=salary_stats.get("count", 0),
                    min_salary=salary_stats.get("min_salary"),
                    max_salary=salary_stats.get("max_salary"),
                    avg_min_salary=salary_stats.get("avg_min_salary"),
                    avg_max_salary=salary_stats.get("avg_max_salary"),
                )

        # 2c. Correct experience statistics (exclude corrupt values > 50)
        exp_stats = fetch_experience_stats_for_query(db, sql)
        if exp_stats:
            safe_stats = _apply_experience_correction(safe_stats, exp_stats)
            if chatbot_logger:
                chatbot_logger.log_section(
                    "AGGREGATION - EXPERIENCE CORRECTION",
                    status="APPLIED",
                    valid_count=exp_stats.get("count", 0),
                    min_experience=exp_stats.get("min_experience"),
                    max_experience=exp_stats.get("max_experience"),
                    avg_experience=exp_stats.get("avg_experience"),
                )

        # Log corrected stats + query execution
        if chatbot_logger:
            chatbot_logger.log_db_stats("AGGREGATION - CORRECTED STATS (sent to LLM)", safe_stats)
            chatbot_logger.log_section(
                "AGGREGATION - QUERY EXECUTION",
                status="SUCCESS",
                stats_rows=len(safe_stats),
            )

        # 3. LLM summarises
        if not safe_stats:
            result = AggregationAgentResult(
                sql=sql,
                explanation=explanation,
                stats=[],
                summary="No data available for the requested statistics.",
                reply="No data was found to compute the requested statistics.",
            )
            if chatbot_logger:
                chatbot_logger.log_section(
                    "AGGREGATION - RESULT",
                    stats_count=0,
                    summary=result.summary,
                    reply=result.reply,
                )
            return result

        summary_data = await summarise_stats(self.llm, message, safe_stats)

        result = AggregationAgentResult(
            sql=sql,
            explanation=explanation,
            stats=safe_stats,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", "Here are the statistics."),
        )

        # Log final result
        if chatbot_logger:
            chatbot_logger.log_section(
                "AGGREGATION - RESULT",
                stats_count=len(safe_stats),
                summary=result.summary,
                reply=result.reply,
            )

        return result
