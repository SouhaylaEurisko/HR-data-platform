"""
Resume service — upload, retrieve, download, delete candidate resumes.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models.candidate import Candidate
from ..models.candidate_resume import CandidateResume, CandidateResumeRead

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

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        raise FileNotFoundError(f"Candidate {candidate_id} not found in org {org_id}.")

    existing = (
        db.query(CandidateResume)
        .filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.organization_id == org_id,
        )
        .first()
    )
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

    resume_info = await _parse_resume(file_data)
    resume.resume_info = resume_info
    db.commit()
    db.refresh(resume)
    return CandidateResumeRead.model_validate(resume)


async def _parse_resume(file_data: bytes) -> dict:
    """Call the resume parser agent. Imported lazily to keep service testable."""
    try:
        from .resume_parser_agent import ResumeParserAgent

        agent = ResumeParserAgent()
        return await agent.parse(file_data)
    except Exception as exc:
        logger.warning("Resume parsing failed (will store empty info): %s", exc)
        return {}


def get_resume(db: Session, candidate_id: int, org_id: int) -> Optional[CandidateResumeRead]:
    resume = (
        db.query(CandidateResume)
        .filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.organization_id == org_id,
        )
        .first()
    )
    if resume is None:
        return None
    return CandidateResumeRead.model_validate(resume)


def get_resume_file(
    db: Session, candidate_id: int, org_id: int
) -> Optional[CandidateResume]:
    """Return the full ORM object (including file_data) for streaming."""
    return (
        db.query(CandidateResume)
        .filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.organization_id == org_id,
        )
        .first()
    )


def delete_resume(db: Session, candidate_id: int, org_id: int) -> bool:
    resume = (
        db.query(CandidateResume)
        .filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.organization_id == org_id,
        )
        .first()
    )
    if resume is None:
        return False
    db.delete(resume)
    db.commit()
    return True
