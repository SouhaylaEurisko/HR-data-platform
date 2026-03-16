"""
Filter Agent — entry point.
1. LLM → SQL   2. Execute SQL   3. LLM → Summary
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .models import FilterAgentResult
from .utils import sanitize_rows, filter_empty_rows, resort_by_salary
from .services.filter import generate_filter_sql, summarise_results
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query, execute_salary_aware_query
from ....config.logger import ChatBotLogger

logger = logging.getLogger(__name__)


class FilterAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> FilterAgentResult:
        # 1. LLM generates SQL
        sql_result = await generate_filter_sql(self.llm, message, conversation_history=conversation_history)
        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")

        # Log SQL generation
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER - SQL GENERATION",
                user_query=message,
                generated_sql=sql,
                explanation=explanation,
            )

        # 2. Execute query (salary-aware: post-filters on expected_salary_text)
        try:
            rows, salary_corrected = execute_salary_aware_query(db, sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Filter query failed: {exc}")
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER - QUERY EXECUTION",
                    status="FAILED",
                    error=str(exc),
                )
            return FilterAgentResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="I could not execute the query. Please rephrase your request.",
                reply="Sorry, I had trouble processing that query. Could you rephrase?",
            )

        safe_rows = sanitize_rows(rows)

        # Detect the sort column, filter out corrupt rows, and re-sort correctly
        sql_upper = sql.upper()
        if "ORDER BY YEARS_EXPERIENCE" in sql_upper:
            safe_rows = filter_empty_rows(safe_rows, required_field="years_experience")
        elif "ORDER BY EXPECTED_SALARY" in sql_upper:
            safe_rows = filter_empty_rows(safe_rows, required_field="expected_salary")
            # The SQL sorted by the corrupt FLOAT column — re-sort by parsed salary text
            descending = "DESC" in sql_upper.split("ORDER BY EXPECTED_SALARY")[1].split("LIMIT")[0]
            safe_rows = resort_by_salary(safe_rows, descending=descending)

        total = len(safe_rows)

        # Log query execution result
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER - QUERY EXECUTION",
                status="SUCCESS",
                rows_found=total,
                salary_post_filter_applied=salary_corrected,
            )
            # Log the actual rows retrieved from DB
            chatbot_logger.log_db_rows("FILTER - DB ROWS RETRIEVED", safe_rows)

        # 3. LLM summarises
        if total == 0:
            result = FilterAgentResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="No candidates matched the criteria.",
                reply="No candidates were found matching your search criteria.",
            )
            if chatbot_logger:
                chatbot_logger.log_section(
                    "FILTER - RESULT",
                    total_found=0,
                    summary=result.summary,
                    reply=result.reply,
                )
            return result

        summary_data = await summarise_results(self.llm, message, safe_rows, total)

        result = FilterAgentResult(
            sql=sql,
            explanation=explanation,
            rows=safe_rows,
            total_found=total,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", f"Found {total} candidate(s)."),
        )

        # Log final result
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER - RESULT",
                total_found=total,
                summary=result.summary,
                reply=result.reply,
            )

        return result
