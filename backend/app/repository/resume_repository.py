"""Candidate resume persistence queries."""

from typing import Any, Dict, Optional, Protocol

from sqlalchemy.orm import Session

from ..models.candidate_resume import CandidateResume


def upsert_resume_for_upload(
    db: Session,
    *,
    candidate_id: int,
    org_id: int,
    filename: str,
    content_type: str,
    file_data: bytes,
) -> CandidateResume:
    """
    Insert or update the single resume row for (candidate_id, org_id).
    Clears resume_info for re-parse; caller sets parsed JSON and commits.
    """
    existing = fetch_resume_by_candidate_and_org(db, candidate_id, org_id)
    if existing:
        existing.filename = filename
        existing.content_type = content_type
        existing.file_data = file_data
        existing.resume_info = {}
        resume = existing
    else:
        resume = CandidateResume(
            candidate_id=candidate_id,
            organization_id=org_id,
            filename=filename,
            content_type=content_type,
            file_data=file_data,
            resume_info={},
        )
        db.add(resume)
    db.flush()
    return resume


def set_resume_parsed_info(resume: CandidateResume, resume_info: Dict[str, Any]) -> None:
    """Assign GPT-extracted JSON (ORM dirty state; caller commits)."""
    resume.resume_info = resume_info


def fetch_resume_by_candidate_and_org(
    db: Session, candidate_id: int, org_id: int
) -> Optional[CandidateResume]:
    return (
        db.query(CandidateResume)
        .filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.organization_id == org_id,
        )
        .first()
    )


def delete_resume_if_exists(db: Session, candidate_id: int, org_id: int) -> bool:
    resume = fetch_resume_by_candidate_and_org(db, candidate_id, org_id)
    if resume is None:
        return False
    db.delete(resume)
    return True


def finalize_resume_upload(db: Session, resume: CandidateResume) -> None:
    """Persist resume row after parsed JSON is set; refresh ORM state for response."""
    db.commit()
    db.refresh(resume)


def delete_resume_for_org_committed(db: Session, candidate_id: int, org_id: int) -> bool:
    """Delete resume for candidate/org if present and commit the transaction."""
    deleted = delete_resume_if_exists(db, candidate_id, org_id)
    if deleted:
        db.commit()
    return deleted


class ResumeRepositoryProtocol(Protocol):
    def upsert_resume_for_upload(
        self,
        *,
        candidate_id: int,
        org_id: int,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> CandidateResume: ...
    def set_resume_parsed_info(self, resume: CandidateResume, resume_info: Dict[str, Any]) -> None: ...
    def fetch_resume_by_candidate_and_org(self, candidate_id: int, org_id: int) -> Optional[CandidateResume]: ...
    def delete_resume_if_exists(self, candidate_id: int, org_id: int) -> bool: ...
    def finalize_resume_upload(self, resume: CandidateResume) -> None: ...
    def delete_resume_for_org_committed(self, candidate_id: int, org_id: int) -> bool: ...


class ResumeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_resume_for_upload(
        self,
        *,
        candidate_id: int,
        org_id: int,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> CandidateResume:
        return upsert_resume_for_upload(
            self._db,
            candidate_id=candidate_id,
            org_id=org_id,
            filename=filename,
            content_type=content_type,
            file_data=file_data,
        )

    def set_resume_parsed_info(self, resume: CandidateResume, resume_info: Dict[str, Any]) -> None:
        set_resume_parsed_info(resume, resume_info)

    def fetch_resume_by_candidate_and_org(self, candidate_id: int, org_id: int) -> Optional[CandidateResume]:
        return fetch_resume_by_candidate_and_org(self._db, candidate_id, org_id)

    def delete_resume_if_exists(self, candidate_id: int, org_id: int) -> bool:
        return delete_resume_if_exists(self._db, candidate_id, org_id)

    def finalize_resume_upload(self, resume: CandidateResume) -> None:
        finalize_resume_upload(self._db, resume)

    def delete_resume_for_org_committed(self, candidate_id: int, org_id: int) -> bool:
        return delete_resume_for_org_committed(self._db, candidate_id, org_id)
