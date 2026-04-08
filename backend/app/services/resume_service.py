"""
Resume service — upload, retrieve, download, delete candidate resumes.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models.candidate_resume import CandidateResume, CandidateResumeRead
from ..repository import candidates_repository, resume_repository

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def upload_resume(
    db: Session,
    candidate_id: int,
    org_id: int,
    filename: str,
    content_type: str,
    file_data: bytes,
) -> CandidateResumeRead:
    """Store a resume PDF and trigger GPT parsing for resume_info."""
    if len(file_data) > _MAX_FILE_SIZE:
        raise ValueError("Resume file exceeds maximum size of 10 MB.")

    candidate = candidates_repository.get_candidate_profile_by_id_org(
        db, candidate_id, org_id
    )
    if candidate is None:
        raise FileNotFoundError(f"Candidate {candidate_id} not found in org {org_id}.")

    resume = resume_repository.upsert_resume_for_upload(
        db,
        candidate_id=candidate_id,
        org_id=org_id,
        filename=filename,
        content_type=content_type,
        file_data=file_data,
    )

    resume_info = await _parse_resume(file_data)
    resume_repository.set_resume_parsed_info(resume, resume_info)
    db.commit()
    db.refresh(resume)
    return CandidateResumeRead.model_validate(resume)


async def _parse_resume(file_data: bytes) -> dict:
    """Call the resume parser agent. Imported lazily to keep service testable."""
    try:
        from ..agent.resume_parser_agent import ResumeParserAgent

        agent = ResumeParserAgent()
        return await agent.parse(file_data)
    except Exception as exc:
        logger.warning("Resume parsing failed (will store empty info): %s", exc)
        return {}


def get_resume(db: Session, candidate_id: int, org_id: int) -> Optional[CandidateResumeRead]:
    resume = resume_repository.fetch_resume_by_candidate_and_org(
        db, candidate_id, org_id
    )
    if resume is None:
        return None
    return CandidateResumeRead.model_validate(resume)


def get_resume_file(
    db: Session, candidate_id: int, org_id: int
) -> Optional[CandidateResume]:
    """Return the full ORM object (including file_data) for streaming."""
    return resume_repository.fetch_resume_by_candidate_and_org(db, candidate_id, org_id)


def delete_resume(db: Session, candidate_id: int, org_id: int) -> bool:
    deleted = resume_repository.delete_resume_if_exists(db, candidate_id, org_id)
    if deleted:
        db.commit()
    return deleted
