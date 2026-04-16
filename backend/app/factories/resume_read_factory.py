"""Map stored resume ORM rows to API read schema."""

from ..models.candidate_resume import CandidateResume
from ..schemas.resume import CandidateResumeRead


def candidate_resume_read_from_orm(resume: CandidateResume) -> CandidateResumeRead:
    return CandidateResumeRead.model_validate(resume)
