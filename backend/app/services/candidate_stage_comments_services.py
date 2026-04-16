"""
HR stage comments — map repository rows to read models (JSONB entries per stage).

Append / update flows stay in candidate_service to avoid circular imports.
"""

from __future__ import annotations

from typing import Dict, List, Protocol

from ..dtos.hr_stage_comments import (
    HrStageCommentsRead,
    hr_stage_comments_latest_only,
    json_rows_to_hr_stage_comments_read,
)
from ..repository.candidate_stage_comments_repository import (
    CandidateStageCommentsRepositoryProtocol,
)


class CandidateStageCommentsServiceProtocol(Protocol):
    def fetch_hr_stage_comments_for_candidate(
        self,
        *,
        org_id: int,
        candidate_id: int,
    ) -> HrStageCommentsRead: ...
    def fetch_hr_stage_comments_for_candidate_ids(
        self,
        *,
        org_id: int,
        candidate_ids: List[int],
        latest_only: bool = False,
    ) -> Dict[int, HrStageCommentsRead]: ...


class CandidateStageCommentsService:
    def __init__(self, repository: CandidateStageCommentsRepositoryProtocol) -> None:
        self._repository = repository

    def fetch_hr_stage_comments_for_candidate(
        self,
        *,
        org_id: int,
        candidate_id: int,
    ) -> HrStageCommentsRead:
        rows = self._repository.list_comments_for_candidate(
            org_id=org_id,
            candidate_id=candidate_id,
        )
        return json_rows_to_hr_stage_comments_read(rows)

    def fetch_hr_stage_comments_for_candidate_ids(
        self,
        *,
        org_id: int,
        candidate_ids: List[int],
        latest_only: bool = False,
    ) -> Dict[int, HrStageCommentsRead]:
        """Bulk load for list (optionally strip to latest entry per stage)."""
        if not candidate_ids:
            return {}
        rows = self._repository.list_comments_for_candidates(
            org_id=org_id,
            candidate_ids=candidate_ids,
        )
        by_cand: Dict[int, list] = {}
        for row in rows:
            by_cand.setdefault(row.candidate_id, []).append(row)
        out: Dict[int, HrStageCommentsRead] = {}
        for cid in candidate_ids:
            full = json_rows_to_hr_stage_comments_read(by_cand.get(cid, []))
            out[cid] = hr_stage_comments_latest_only(full) if latest_only else full
        return out
