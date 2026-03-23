"""
Candidate Comparison Agent — recommend the best candidate among a set (same or similar role).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...utils.llm_client import LLMClient
from ..filter_agent.utils import sanitize_rows
from .prompts import COMPARISON_DECIDE_PROMPT, COMPARISON_EXTRACT_PROMPT
from ....config.logger import ChatBotLogger

logger = logging.getLogger(__name__)

_MAX_CANDIDATES = 18
_FETCH_SQL_TEMPLATE = """
SELECT
  c.id,
  c.full_name,
  c.applied_position,
  c.years_of_experience,
  c.tech_stack,
  c.notice_period,
  c.is_open_for_relocation,
  c.expected_salary_remote,
  c.expected_salary_onsite,
  c.is_overtime_flexible,
  c.is_contract_flexible,
  c.is_employed,
  c.has_transportation,
  c.nationality
FROM candidate c
WHERE {where_clause}
ORDER BY c.years_of_experience DESC NULLS LAST, c.created_at DESC
LIMIT :lim
"""


class CandidateComparisonAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def process(
        self,
        message: str,
        db: Session,
        chatbot_logger: Optional[ChatBotLogger] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if chatbot_logger:
            chatbot_logger.log_section("CANDIDATE COMPARISON", user_message=message)

        try:
            ext = await self.llm.call(
                COMPARISON_EXTRACT_PROMPT,
                message,
                context="Comparison extract",
                conversation_history=conversation_history,
            )
        except RuntimeError as exc:
            logger.warning("Comparison extract failed: %s", exc)
            return {
                "reply": "I could not parse which candidates to compare. Name the people or the job title.",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": str(exc),
            }

        names = ext.get("candidate_names") or []
        if not isinstance(names, list):
            names = []
        names = [str(n).strip() for n in names if str(n).strip()]
        position = str(ext.get("position_filter") or "").strip()
        scope = str(ext.get("scope") or "named_only").strip()
        if scope not in ("named_only", "best_for_position"):
            scope = "named_only"

        if scope == "named_only" and not names:
            return {
                "reply": "Please name the candidates to compare, or ask who is the best applicant for a specific job title.",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": "no names",
            }

        where_parts: List[str] = ["1=1"]
        params: Dict[str, Any] = {"lim": _MAX_CANDIDATES}

        if names:
            ors = []
            for i, n in enumerate(names[:12]):
                key = f"nm{i}"
                ors.append(f"c.full_name ILIKE :{key}")
                params[key] = f"%{n}%"
            where_parts.append("(" + " OR ".join(ors) + ")")

        if position:
            where_parts.append("c.applied_position ILIKE :pos")
            params["pos"] = f"%{position}%"

        if scope == "best_for_position" and not position:
            return {
                "reply": "Which position or role should I use to find applicants to compare?",
                "summary": None,
                "sql": None,
                "rows": [],
                "total_found": 0,
                "explanation": "best_for_position without position",
            }

        where_clause = " AND ".join(where_parts)
        sql = _FETCH_SQL_TEMPLATE.format(where_clause=where_clause)

        try:
            rows = list(db.execute(text(sql), params).mappings())
        except Exception as exc:
            logger.exception("Comparison fetch failed: %s", exc)
            return {
                "reply": "I could not load candidate profiles for comparison.",
                "summary": None,
                "sql": sql,
                "rows": [],
                "total_found": 0,
                "explanation": str(exc),
            }

        if len(rows) < 2:
            return {
                "reply": (
                    "I need at least **two** matching candidates to compare. "
                    f"Found {len(rows)}. Try broader names or a different job title filter."
                ),
                "summary": None,
                "sql": sql,
                "rows": sanitize_rows([dict(r) for r in rows]),
                "total_found": len(rows),
                "explanation": "too few rows",
            }

        ids = [int(r["id"]) for r in rows if r.get("id") is not None]
        hr_map = _load_hr_summaries(db, ids)

        profiles: List[Dict[str, Any]] = []
        for r in rows:
            rid = r["id"]
            profiles.append(
                {
                    "full_name": r.get("full_name"),
                    "applied_position": r.get("applied_position"),
                    "years_of_experience": float(r["years_of_experience"])
                    if r.get("years_of_experience") is not None
                    else None,
                    "tech_stack": r.get("tech_stack"),
                    "notice_period": r.get("notice_period"),
                    "is_open_for_relocation": r.get("is_open_for_relocation"),
                    "expected_salary_remote": float(r["expected_salary_remote"])
                    if r.get("expected_salary_remote") is not None
                    else None,
                    "expected_salary_onsite": float(r["expected_salary_onsite"])
                    if r.get("expected_salary_onsite") is not None
                    else None,
                    "is_overtime_flexible": r.get("is_overtime_flexible"),
                    "is_contract_flexible": r.get("is_contract_flexible"),
                    "is_employed": r.get("is_employed"),
                    "has_transportation": r.get("has_transportation"),
                    "nationality": r.get("nationality"),
                    "hr_comment_summary": hr_map.get(int(rid), ""),
                }
            )

        user_payload = (
            "User question:\n"
            + message
            + "\n\nCandidate profiles (JSON):\n"
            + json.dumps(profiles, default=str, indent=2)
        )

        try:
            decision = await self.llm.call(
                COMPARISON_DECIDE_PROMPT,
                user_payload,
                context="Comparison decision",
                temperature=0.3,
                conversation_history=None,
            )
        except RuntimeError as exc:
            logger.warning("Comparison LLM failed: %s", exc)
            return {
                "reply": "I loaded the candidates but could not finish the analysis. Please try again.",
                "summary": None,
                "sql": sql,
                "rows": sanitize_rows([dict(r) for r in rows]),
                "total_found": len(rows),
                "explanation": str(exc),
            }

        reply = str(decision.get("reply") or "I could not determine a single best candidate.")
        summary = decision.get("summary")
        rec_name = decision.get("recommended_full_name")
        chosen = _match_recommended_row(rows, rec_name)

        if chosen:
            card_rows = sanitize_rows([dict(chosen)])
            total_for_ui = 1
        else:
            card_rows = []
            total_for_ui = 0

        return {
            "reply": reply,
            "summary": summary,
            "sql": sql,
            "rows": card_rows,
            "total_found": total_for_ui,
            "explanation": "comparison complete",
        }


def _match_recommended_row(
    rows: List[Mapping[str, Any]],
    recommended_name: Any,
) -> Optional[Mapping[str, Any]]:
    """Map LLM recommended_full_name to one DB row; None if no confident match."""
    if not rows:
        return None
    name = str(recommended_name or "").strip()
    if not name:
        return None
    target = name.lower()

    for r in rows:
        fn = str(r.get("full_name") or "").strip()
        if fn.lower() == target:
            return r

    substr_matches = [r for r in rows if target in str(r.get("full_name") or "").lower()]
    if len(substr_matches) == 1:
        return substr_matches[0]

    parts = target.split()
    if len(parts) >= 2:
        token_hits = [
            r2
            for r2 in rows
            if all(p in str(r2.get("full_name") or "").lower() for p in parts[:2])
        ]
        if len(token_hits) == 1:
            return token_hits[0]

    return None


def _load_hr_summaries(db: Session, candidate_ids: List[int]) -> Dict[int, str]:
    if not candidate_ids:
        return {}
    # Simple IN clause — ids are integers from our DB only
    id_list = ",".join(str(i) for i in candidate_ids[:50])
    q = text(
        f"""
        SELECT candidate_id, stage_key, entries
        FROM candidate_stage_comment
        WHERE candidate_id IN ({id_list})
        """
    )
    out: Dict[int, List[str]] = {cid: [] for cid in candidate_ids}
    try:
        for row in db.execute(q).mappings():
            cid = int(row["candidate_id"])
            if cid not in out:
                continue
            entries_raw = row["entries"]
            if isinstance(entries_raw, str):
                try:
                    entries = json.loads(entries_raw)
                except json.JSONDecodeError:
                    entries = []
            else:
                entries = list(entries_raw) if isinstance(entries_raw, list) else []
            if not entries:
                continue
            latest = entries[-1] if isinstance(entries[-1], dict) else {}
            txt = str(latest.get("text") or "").strip()
            if txt:
                stage = str(row.get("stage_key") or "")
                out[cid].append(f"{stage}: {txt[:200]}")
    except Exception as exc:
        logger.warning("HR summary load skipped: %s", exc)
        return {}

    return {cid: " | ".join(parts) if parts else "" for cid, parts in out.items()}
