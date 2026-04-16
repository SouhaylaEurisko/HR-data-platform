"""
Repository dependency providers.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from ..config import get_db
from ..repository.analytics_repository import AnalyticsRepository, AnalyticsRepositoryProtocol
from ..repository.auth_repository import AuthRepository, AuthRepositoryProtocol
from ..repository.candidate_stage_comments_repository import (
    CandidateStageCommentsRepository,
    CandidateStageCommentsRepositoryProtocol,
)
from ..repository.candidates_repository import CandidatesRepository, CandidatesRepositoryProtocol
from ..repository.column_normalizer_repository import (
    ColumnNormalizerRepository,
    ColumnNormalizerRepositoryProtocol,
)
from ..repository.custom_fields_repository import (
    CustomFieldsRepository,
    CustomFieldsRepositoryProtocol,
)
from ..repository.import_repository import ImportRepository, ImportRepositoryProtocol
from ..repository.lookups_repository import LookupsRepository, LookupsRepositoryProtocol
from ..repository.resume_repository import ResumeRepository, ResumeRepositoryProtocol


def get_auth_repository(db: Session = Depends(get_db)) -> AuthRepositoryProtocol:
    return AuthRepository(db)


def get_candidates_repository(db: Session = Depends(get_db)) -> CandidatesRepositoryProtocol:
    return CandidatesRepository(db)


def get_analytics_repository(db: Session = Depends(get_db)) -> AnalyticsRepositoryProtocol:
    return AnalyticsRepository(db)


def get_resume_repository(db: Session = Depends(get_db)) -> ResumeRepositoryProtocol:
    return ResumeRepository(db)


def get_lookups_repository(db: Session = Depends(get_db)) -> LookupsRepositoryProtocol:
    return LookupsRepository(db)


def get_custom_fields_repository(db: Session = Depends(get_db)) -> CustomFieldsRepositoryProtocol:
    return CustomFieldsRepository(db)


def get_candidate_stage_comments_repository(
    db: Session = Depends(get_db),
) -> CandidateStageCommentsRepositoryProtocol:
    return CandidateStageCommentsRepository(db)


def get_column_normalizer_repository(
    db: Session = Depends(get_db),
) -> ColumnNormalizerRepositoryProtocol:
    return ColumnNormalizerRepository(db)


def get_import_repository(db: Session = Depends(get_db)) -> ImportRepositoryProtocol:
    return ImportRepository(db)
