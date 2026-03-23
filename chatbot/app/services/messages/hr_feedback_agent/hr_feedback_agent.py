"""
HR Feedback Agent — latest pipeline comment for a candidate at a given stage.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...utils.llm_client import LLMClient
from ..filter_agent.utils import sanitize_rows
from .prompts import HR_FEEDBACK_EXTRACT_PROMPT
from ....config.logger import ChatBotLogger

logger = logging.getLogger(__name__)

_STAGE_LABELS = {
    "pre_screening": "Pre Screening",
    "technical_interview": "Technical Interview",
    "hr_interview": "HR Interview",
    "offer_stage": "Offer Stage",
}


class HrFeedbackAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Returns dict: reply, summary (optional), sql (debug), rows (optional), total_found, explanation.
        """
        if chatbot_logger:
            chatbot_logger.log_section("HR FEEDBACK", user_message=message)

        try:
            data = await self.llm.call(
                HR_FEEDBACK_EXTRACT_PROMPT,
                message,
                context="HR feedback extract",
                conversation_history=conversation_history,
            )
        except RuntimeError as exc:
            logger.warning("HR feedback extract failed: %s", exc)
            return {
                "reply": "I could not understand which candidate and stage you mean. Please name the person and the stage (e.g. pre-screening).",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": str(exc),
            }

        name = (data.get("candidate_name") or "").strip()
        stage = (data.get("stage") or "pre_screening").strip()
        if stage not in _STAGE_LABELS:
            stage = "pre_screening"

        if not name:
            return {
                "reply": "Please tell me which candidate’s HR feedback you want (e.g. their full name).",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": "missing candidate_name",
            }

        sql_debug = (
            "SELECT c.full_name, csc.stage_key, csc.entries "
            "FROM candidate c JOIN candidate_stage_comment csc "
            "ON c.id = csc.candidate_id AND c.organization_id = csc.organization_id "
            "WHERE c.full_name ILIKE :pat AND csc.stage_key = :stage LIMIT 5"
        )

        try:
            rows = list(
                db.execute(
                    text(sql_debug),
                    {"pat": f"%{name}%", "stage": stage},
                ).mappings()
            )
        except Exception as exc:
            logger.exception("HR feedback query failed: %s", exc)
            return {
                "reply": "I could not read HR comments from the database. If the issue persists, contact support.",
                "summary": None,
                "sql": sql_debug,
                "rows": [],
                "total_found": 0,
                "explanation": str(exc),
            }

        if not rows:
            label = _STAGE_LABELS[stage]
            return {
                "reply": (
                    f"I found no **{label}** comments stored for a candidate matching “{name}”. "
                    "Check the spelling or add a comment on the candidate’s detail page first."
                ),
                "summary": None,
                "sql": sql_debug,
                "rows": [],
                "total_found": 0,
                "explanation": "no matching rows",
            }

        if len(rows) > 1:
            names = list({r["full_name"] or "—" for r in rows})
            return {
                "reply": (
                    f"Several candidates matched “{name}”: {', '.join(names[:5])}. "
                    "Please use a more specific name so I can pick the right person."
                ),
                "summary": None,
                "sql": sql_debug,
                "rows": sanitize_rows([dict(r) for r in rows]),
                "total_found": len(rows),
                "explanation": "ambiguous match",
            }

        row = rows[0]
        full_name = row["full_name"] or name
        entries_raw = row["entries"]
        entries: List[Any]
        if entries_raw is None:
            entries = []
        elif isinstance(entries_raw, str):
            try:
                entries = json.loads(entries_raw)
            except json.JSONDecodeError:
                entries = []
        else:
            entries = list(entries_raw) if isinstance(entries_raw, list) else []

        if not entries:
            label = _STAGE_LABELS[stage]
            return {
                "reply": f"There is a **{label}** record for **{full_name}**, but it has no comment text yet.",
                "summary": None,
                "sql": sql_debug,
                "rows": None,
                "total_found": 0,
                "explanation": "empty entries",
            }

        latest = entries[-1]
        if not isinstance(latest, dict):
            latest = {}
        comment_text = str(latest.get("text") or "").strip()
        created = latest.get("created_at")
        date_str = _format_comment_date(created)

        label = _STAGE_LABELS[stage]
        if not comment_text:
            return {
                "reply": (
                    f"There is a **{label}** record for **{full_name}** on **{date_str}**, "
                    "but the latest entry has no text."
                ),
                "summary": None,
                "sql": sql_debug,
                "rows": None,
                "total_found": 0,
                "explanation": "empty latest text",
            }

        # Main bubble: context only. Comment body goes to `summary` (purple box in HR UI).
        reply = f"**Latest {label} feedback for {full_name}** ({date_str})"

        return {
            "reply": reply,
            "summary": comment_text,
            "sql": sql_debug,
            "rows": None,
            "total_found": 0,
            "explanation": "success",
        }


def _format_comment_date(raw: Any) -> str:
    if raw is None:
        return "date unknown"
    if isinstance(raw, datetime):
        return raw.strftime("%B %d, %Y")
    s = str(raw).strip()
    if not s:
        return "date unknown"
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except ValueError:
        return s
