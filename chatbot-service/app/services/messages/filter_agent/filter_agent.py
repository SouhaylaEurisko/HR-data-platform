"""
Filter Agent — entry point.
1. LLM → SQL   2. Execute SQL   3. LLM → Summary
"""
import logging
from sqlalchemy.orm import Session

from .models import FilterAgentResult
from .utils import sanitize_rows
from .services.filter import generate_filter_sql, summarise_results
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query

logger = logging.getLogger(__name__)


class FilterAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def process(self, message: str, db: Session) -> FilterAgentResult:
        # 1. LLM generates SQL
        sql_result = await generate_filter_sql(self.llm, message)
        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")

        # 2. Execute query
        try:
            rows = execute_safe_query(db, sql)
        except (ValueError, RuntimeError) as exc:
            logger.error(f"Filter query failed: {exc}")
            return FilterAgentResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="I could not execute the query. Please rephrase your request.",
                reply="Sorry, I had trouble processing that query. Could you rephrase?",
            )

        safe_rows = sanitize_rows(rows)
        total = len(safe_rows)

        # 3. LLM summarises
        if total == 0:
            return FilterAgentResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="No candidates matched the criteria.",
                reply="No candidates were found matching your search criteria.",
            )

        summary_data = await summarise_results(self.llm, message, safe_rows, total)

        return FilterAgentResult(
            sql=sql,
            explanation=explanation,
            rows=safe_rows,
            total_found=total,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", f"Found {total} candidate(s)."),
        )
