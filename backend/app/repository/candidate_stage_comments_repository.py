"""Queries for candidate_stage_comment rows."""

from typing import List, Protocol

from sqlalchemy.orm import Session

from ..models.candidate_stage_comment import CandidateStageComment


def list_comments_for_candidate(
    db: Session,
    *,
    org_id: int,
    candidate_id: int,
) -> List[CandidateStageComment]:
    return (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
        )
        .all()
    )


def list_comments_for_candidates(
    db: Session,
    *,
    org_id: int,
    candidate_ids: List[int],
) -> List[CandidateStageComment]:
    if not candidate_ids:
        return []
    return (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.candidate_id.in_(candidate_ids),
        )
        .all()
    )


class CandidateStageCommentsRepositoryProtocol(Protocol):
    def list_comments_for_candidate(
        self,
        *,
        org_id: int,
        candidate_id: int,
    ) -> List[CandidateStageComment]: ...
    def list_comments_for_candidates(
        self,
        *,
        org_id: int,
        candidate_ids: List[int],
    ) -> List[CandidateStageComment]: ...


class CandidateStageCommentsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_comments_for_candidate(
        self,
        *,
        org_id: int,
        candidate_id: int,
    ) -> List[CandidateStageComment]:
        return list_comments_for_candidate(self._db, org_id=org_id, candidate_id=candidate_id)

    def list_comments_for_candidates(
        self,
        *,
        org_id: int,
        candidate_ids: List[int],
    ) -> List[CandidateStageComment]:
        return list_comments_for_candidates(self._db, org_id=org_id, candidate_ids=candidate_ids)
