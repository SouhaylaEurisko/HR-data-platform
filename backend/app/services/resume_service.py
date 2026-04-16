"""
Resume service — upload, retrieve, download, delete candidate resumes.
"""

import logging
from typing import Optional, Protocol

from ..constants import ResumeUpload
from ..models.candidate_resume import CandidateResume
from ..repository.candidates_repository import CandidatesRepositoryProtocol
from ..repository.resume_repository import ResumeRepositoryProtocol
from ..schemas.resume import CandidateResumeRead

logger = logging.getLogger(__name__)

class ResumeServiceProtocol(Protocol):
    async def upload_resume(
        self,
        candidate_id: int,
        org_id: int,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> CandidateResumeRead: ...
    def get_resume(self, candidate_id: int, org_id: int) -> Optional[CandidateResumeRead]: ...
    def get_resume_file(self, candidate_id: int, org_id: int) -> Optional[CandidateResume]: ...
    def delete_resume(self, candidate_id: int, org_id: int) -> bool: ...


class ResumeService:
    def __init__(
        self,
        candidates_repo: CandidatesRepositoryProtocol,
        resume_repo: ResumeRepositoryProtocol,
    ) -> None:
        self._candidates_repo = candidates_repo
        self._resume_repo = resume_repo

    async def upload_resume(
        self,
        candidate_id: int,
        org_id: int,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> CandidateResumeRead:
        """Store a resume PDF and trigger GPT parsing for resume_info."""
        if len(file_data) > ResumeUpload.MAX_FILE_BYTES:
            raise ValueError("Resume file exceeds maximum size of 10 MB.")

        candidate = self._candidates_repo.get_candidate_profile_by_id_org(candidate_id, org_id)
        if candidate is None:
            raise FileNotFoundError(f"Candidate {candidate_id} not found in org {org_id}.")

        resume = self._resume_repo.upsert_resume_for_upload(
            candidate_id=candidate_id,
            org_id=org_id,
            filename=filename,
            content_type=content_type,
            file_data=file_data,
        )

        resume_info = await _parse_resume(file_data)
        self._resume_repo.set_resume_parsed_info(resume, resume_info)
        self._resume_repo.finalize_resume_upload(resume)
        return CandidateResumeRead.model_validate(resume)

    def get_resume(self, candidate_id: int, org_id: int) -> Optional[CandidateResumeRead]:
        resume = self._resume_repo.fetch_resume_by_candidate_and_org(candidate_id, org_id)
        if resume is None:
            return None
        return CandidateResumeRead.model_validate(resume)

    def get_resume_file(self, candidate_id: int, org_id: int) -> Optional[CandidateResume]:
        return self._resume_repo.fetch_resume_by_candidate_and_org(candidate_id, org_id)

    def delete_resume(self, candidate_id: int, org_id: int) -> bool:
        return self._resume_repo.delete_resume_for_org_committed(candidate_id, org_id)

async def _parse_resume(file_data: bytes) -> dict:
    """Call the resume parser agent. Imported lazily to keep service testable."""
    try:
        from ..agent.resume_parser_agent import ResumeParserAgent

        agent = ResumeParserAgent()
        return await agent.parse(file_data)
    except Exception as exc:
        logger.warning("Resume parsing failed (will store empty info): %s", exc)
        return {}

