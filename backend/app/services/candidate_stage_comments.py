"""
Load candidate HR stage comments (one DB row per stage; entries in JSONB).

Append is implemented in candidate_service to avoid circular imports.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from ..models.candidate_stage_comment import (
    CandidateStageComment,
    HrStageCommentsRead,
    hr_stage_comments_latest_only,
    json_rows_to_hr_stage_comments_read,
)


def fetch_hr_stage_comments_for_candidate(
    db: Session,
    *,
    org_id: int,
    candidate_id: int,
) -> HrStageCommentsRead:
    rows = (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
        )
        .all()
    )
    return json_rows_to_hr_stage_comments_read(rows)


def fetch_hr_stage_comments_for_candidate_ids(
    db: Session,
    *,
    org_id: int,
    candidate_ids: List[int],
    latest_only: bool = False,
) -> Dict[int, HrStageCommentsRead]:
    """Bulk load for list (optionally strip to latest entry per stage)."""
    if not candidate_ids:
        return {}
    rows = (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.candidate_id.in_(candidate_ids),
        )
        .all()
    )
    by_cand: Dict[int, list] = {}
    for r in rows:
        by_cand.setdefault(r.candidate_id, []).append(r)
    out: Dict[int, HrStageCommentsRead] = {}
    for cid in candidate_ids:
        full = json_rows_to_hr_stage_comments_read(by_cand.get(cid, []))
        out[cid] = hr_stage_comments_latest_only(full) if latest_only else full
    return out
