"""
CV Info Agent — retrieves and summarises candidate details with resume/CV data.

Pipeline:
1. LLM extracts candidate name (or detects a resume content search)
2. LLM generates SQL with candidate_resume JOIN
3. Execute SQL
4. LLM summarises the profile + CV data
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .models import CvInfoResult
from .prompts import CV_INFO_EXTRACT_PROMPT, CV_INFO_SQL_PROMPT, CV_INFO_SUMMARY_PROMPT
from .utils import cv_rows_to_display
from ..filter_agent.utils import sanitize_rows
from ...utils.llm_client import LLMClient
from ...utils.db_utils import execute_safe_query
from ....config.logger import ChatBotLogger

logger = logging.getLogger(__name__)


class CvInfoAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> CvInfoResult:
        if chatbot_logger:
            chatbot_logger.log_section("CV INFO", user_message=message)

        # 1. Extract candidate name
        try:
            extraction = await self.llm.call(
                CV_INFO_EXTRACT_PROMPT,
                message,
                context="CV info name extraction",
                conversation_history=conversation_history,
            )
        except RuntimeError as exc:
            logger.warning("CV info extraction failed: %s", exc)
            return CvInfoResult(
                sql="",
                explanation=str(exc),
                rows=[],
                total_found=0,
                summary="",
                reply="I could not understand your request. Please mention a candidate name or what you're looking for in resumes.",
            )

        candidate_name = (extraction.get("candidate_name") or "").strip()
        question_type = (extraction.get("question_type") or "profile").strip()

        if chatbot_logger:
            chatbot_logger.log_section(
                "CV INFO - EXTRACTION",
                extracted_name=candidate_name or "(none — resume content search)",
                question_type=question_type,
            )

        # 2. Generate SQL
        try:
            sql_result = await self.llm.call(
                CV_INFO_SQL_PROMPT,
                message,
                context="CV info SQL generation",
                conversation_history=conversation_history,
            )
        except RuntimeError as exc:
            logger.warning("CV info SQL generation failed: %s", exc)
            return CvInfoResult(
                sql="",
                explanation=str(exc),
                rows=[],
                total_found=0,
                summary="",
                reply="I had trouble generating the query. Please try rephrasing your request.",
            )

        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")

        if chatbot_logger:
            chatbot_logger.log_section(
                "CV INFO - SQL GENERATION",
                user_query=message,
                generated_sql=sql,
                explanation=explanation,
            )

        # 3. Execute query
        try:
            rows = execute_safe_query(db, sql)
        except (ValueError, RuntimeError) as exc:
            logger.error("CV info query failed: %s", exc)
            if chatbot_logger:
                chatbot_logger.log_section(
                    "CV INFO - QUERY EXECUTION",
                    status="FAILED",
                    error=str(exc),
                )
            return CvInfoResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="",
                reply="I could not execute the query. Please rephrase your request.",
            )

        safe_rows = sanitize_rows(rows)
        total = len(safe_rows)

        if chatbot_logger:
            chatbot_logger.log_section(
                "CV INFO - QUERY EXECUTION",
                status="SUCCESS",
                rows_found=total,
            )
            chatbot_logger.log_db_rows("CV INFO - DB ROWS RETRIEVED", safe_rows)

        # 4. Summarise
        if total == 0:
            no_results_reply = (
                f"I couldn't find any candidate matching \"{candidate_name}\" with resume data."
                if candidate_name
                else "No candidates were found matching your resume search criteria."
            )
            result = CvInfoResult(
                sql=sql,
                explanation=explanation,
                rows=[],
                total_found=0,
                summary="No candidates matched the criteria.",
                reply=no_results_reply,
            )
            if chatbot_logger:
                chatbot_logger.log_section(
                    "CV INFO - RESULT",
                    total_found=0,
                    reply=result.reply,
                )
            return result

        display = cv_rows_to_display(safe_rows)
        prompt_input = (
            f"User asked: {message}\n"
            f"Total candidates found: {total}\n\n"
            f"Results:\n{display}"
        )

        try:
            summary_data = await self.llm.call(
                CV_INFO_SUMMARY_PROMPT,
                prompt_input,
                context="CV info summary",
                temperature=0.4,
            )
        except RuntimeError as exc:
            logger.warning("CV info summary failed: %s", exc)
            summary_data = {
                "summary": f"Found {total} candidate(s) with resume data.",
                "reply": f"Found {total} candidate(s).",
            }

        include_rows = question_type == "profile"

        result = CvInfoResult(
            sql=sql,
            explanation=explanation,
            rows=safe_rows if include_rows else None,
            total_found=total,
            summary=summary_data.get("summary", ""),
            reply=summary_data.get("reply", f"Found {total} candidate(s)."),
        )

        if chatbot_logger:
            chatbot_logger.log_section(
                "CV INFO - RESULT",
                total_found=total,
                summary=result.summary,
                reply=result.reply,
            )

        return result
