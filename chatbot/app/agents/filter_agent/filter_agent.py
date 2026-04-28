"""
Filter Agent — entry point.
1. LLM → SQL   2. Execute SQL   3. LLM → Summary
"""
import logging
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .models import FilterAgentResult
from .filter_service import FilterService
from .utils import sanitize_rows, filter_empty_rows, resort_by_salary
from ...utils.db_utils import execute_salary_aware_query
from ...config.logger import ChatBotLogger

logger = logging.getLogger(__name__)


class FilterAgent:
    def __init__(self, service: FilterService) -> None:
        self._service = service

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> FilterAgentResult:
        # 1. LLM generates SQL
        sql_result = await self._service.generate_filter_sql(
            message, conversation_history=conversation_history
        )
        sql = sql_result.sql
        explanation = sql_result.explanation

        # Log SQL generation
        if chatbot_logger:
            chatbot_logger.log_section(
                "FILTER - SQL GENERATION",
                user_query=message,
                generated_sql=sql,
                explanation=explanation,
            )

        # 2. Execute query (salary-aware: post-filters on current_salary when needed)
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
        if re.search(r"ORDER\s+BY[\s\S]{0,120}YEARS_OF_EXPERIENCE", sql_upper):
            safe_rows = filter_empty_rows(safe_rows, required_field="years_of_experience")
        elif re.search(r"ORDER\s+BY[\s\S]{0,120}CURRENT_SALARY", sql_upper):
            safe_rows = filter_empty_rows(safe_rows, required_field="current_salary")
            m = re.search(
                r"ORDER\s+BY[\s\S]{0,120}CURRENT_SALARY([\s\S]{0,80}?)(?:LIMIT|\Z)",
                sql_upper,
            )
            tail = m.group(1) if m else ""
            descending = "DESC" in tail
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

        summary_data = await self._service.summarise_results(message, safe_rows, total)

        result = FilterAgentResult(
            sql=sql,
            explanation=explanation,
            rows=safe_rows,
            total_found=total,
            summary=summary_data.summary,
            reply=summary_data.reply or f"Found {total} candidate(s).",
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
