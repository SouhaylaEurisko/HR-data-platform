"""
HR Feedback Agent — latest pipeline comment for a candidate at a given stage.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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

# When two stages share the same latest-entry timestamp, prefer a later pipeline stage.
_STAGE_TIEBREAK_RANK = {
    "pre_screening": 0,
    "technical_interview": 1,
    "hr_interview": 2,
    "offer_stage": 3,
}

_SQL_BY_STAGE = (
    "SELECT c.id, c.full_name, csc.stage_key, csc.entries "
    "FROM candidate c JOIN candidate_stage_comment csc "
    "ON c.id = csc.candidate_id AND c.organization_id = csc.organization_id "
    "WHERE c.full_name ILIKE :pat AND csc.stage_key = :stage LIMIT 5"
)

_SQL_ALL_STAGES_FOR_NAME = (
    "SELECT c.id, c.full_name, csc.stage_key, csc.entries "
    "FROM candidate c JOIN candidate_stage_comment csc "
    "ON c.id = csc.candidate_id AND c.organization_id = csc.organization_id "
    "WHERE c.full_name ILIKE :pat"
)


def _parse_entry_datetime(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _entries_as_list(entries_raw: Any) -> List[Any]:
    if entries_raw is None:
        return []
    if isinstance(entries_raw, str):
        try:
            raw = json.loads(entries_raw)
        except json.JSONDecodeError:
            return []
        return list(raw) if isinstance(raw, list) else []
    if isinstance(entries_raw, list):
        return list(entries_raw)
    return []


def _latest_nonempty_entry_dict(entries: List[Any]) -> Optional[Dict[str, Any]]:
    """Newest comment object (array is oldest → newest)."""
    for item in reversed(entries):
        if isinstance(item, dict) and str(item.get("text") or "").strip():
            return item
    return None


def _latest_nonempty_entry_time(entries_raw: Any) -> Optional[datetime]:
    """Time of the newest comment entry (array is oldest → newest)."""
    ent = _latest_nonempty_entry_dict(_entries_as_list(entries_raw))
    if not ent:
        return None
    return _parse_entry_datetime(ent.get("created_at"))


def _pick_row_latest_comment_stage(rows: List[Any]) -> Optional[Any]:
    """Among rows (same or mixed candidates), pick the row whose stage has the latest comment."""
    best_key: Optional[tuple] = None
    best_row: Optional[Any] = None
    for row in rows:
        sk = row.get("stage_key")
        if sk not in _STAGE_LABELS:
            continue
        ts = _latest_nonempty_entry_time(row.get("entries"))
        if ts is None:
            continue
        rank = _STAGE_TIEBREAK_RANK[sk]
        key = (ts, rank)
        if best_key is None or key > best_key:
            best_key = key
            best_row = row
    return best_row


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
        raw_stage = data.get("stage")
        stage_explicit: Optional[str] = None
        if raw_stage is not None:
            s = str(raw_stage).strip()
            if s in _STAGE_LABELS:
                stage_explicit = s

        if not name:
            return {
                "reply": "Please tell me which candidate’s HR feedback you want (e.g. their full name).",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": "missing candidate_name",
            }

        pat = f"%{name}%"
        sql_debug = _SQL_BY_STAGE if stage_explicit else _SQL_ALL_STAGES_FOR_NAME

        try:
            if stage_explicit is not None:
                rows = list(
                    db.execute(
                        text(_SQL_BY_STAGE),
                        {"pat": pat, "stage": stage_explicit},
                    ).mappings()
                )
                if not rows:
                    label = _STAGE_LABELS[stage_explicit]
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
                stage = stage_explicit
            else:
                all_rows = list(
                    db.execute(
                        text(_SQL_ALL_STAGES_FOR_NAME),
                        {"pat": pat},
                    ).mappings()
                )
                if not all_rows:
                    return {
                        "reply": (
                            f"I found no HR stage comments stored for a candidate matching “{name}”. "
                            "Check the spelling or add notes on the candidate’s detail page first."
                        ),
                        "summary": None,
                        "sql": sql_debug,
                        "rows": [],
                        "total_found": 0,
                        "explanation": "no matching rows",
                    }
                by_id: Dict[int, List[Any]] = {}
                for r in all_rows:
                    cid = int(r["id"])
                    by_id.setdefault(cid, []).append(r)
                if len(by_id) > 1:
                    names = list({r["full_name"] or "—" for r in all_rows})
                    return {
                        "reply": (
                            f"Several candidates matched “{name}”: {', '.join(names[:5])}. "
                            "Please use a more specific name so I can pick the right person."
                        ),
                        "summary": None,
                        "sql": sql_debug,
                        "rows": sanitize_rows([dict(r) for r in all_rows]),
                        "total_found": len(all_rows),
                        "explanation": "ambiguous match",
                    }
                cand_rows = next(iter(by_id.values()))
                picked = _pick_row_latest_comment_stage(cand_rows)
                if picked is None:
                    fn = str(cand_rows[0].get("full_name") or name).strip() or name
                    return {
                        "reply": (
                            f"There are HR stage records for **{fn}**, but **no comment text** has been added in any stage yet."
                        ),
                        "summary": None,
                        "sql": sql_debug,
                        "rows": None,
                        "total_found": 0,
                        "explanation": "no comment text in any stage",
                    }
                row = picked
                stage = str(picked["stage_key"])

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

        full_name = row["full_name"] or name
        entries = _entries_as_list(row.get("entries"))
        latest = _latest_nonempty_entry_dict(entries)
        if not latest:
            label = _STAGE_LABELS[stage]
            return {
                "reply": f"There is a **{label}** record for **{full_name}**, but it has no comment text yet.",
                "summary": None,
                "sql": sql_debug,
                "rows": None,
                "total_found": 0,
                "explanation": "empty entries",
            }

        comment_text = str(latest.get("text") or "").strip()
        created = latest.get("created_at")
        date_str = _format_comment_date(created)
        label = _STAGE_LABELS[stage]

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
