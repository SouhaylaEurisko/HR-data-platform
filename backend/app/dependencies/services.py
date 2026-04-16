"""
Service dependency providers.
"""
from fastapi import Depends

from ..repository.auth_repository import AuthRepositoryProtocol
from ..repository.analytics_repository import AnalyticsRepositoryProtocol
from ..repository.candidates_repository import CandidatesRepositoryProtocol
from ..repository.candidate_stage_comments_repository import CandidateStageCommentsRepositoryProtocol
from ..repository.custom_fields_repository import CustomFieldsRepositoryProtocol
from ..repository.lookups_repository import LookupsRepositoryProtocol
from ..repository.resume_repository import ResumeRepositoryProtocol
from ..repository.import_repository import ImportRepositoryProtocol
from ..repository.column_normalizer_repository import ColumnNormalizerRepositoryProtocol
from ..services.analytics_service import AnalyticsService, AnalyticsServiceProtocol
from ..services.auth_service import AuthService, AuthServiceProtocol
from ..services.candidate_service import CandidateService, CandidateServiceProtocol
from ..services.custom_field_type_service import (
    CustomFieldTypeService,
    CustomFieldTypeServiceProtocol,
)
from ..services.import_service import ImportService, ImportServiceProtocol
from ..services.lookup_service import LookupService, LookupServiceProtocol
from ..services.resume_service import ResumeService, ResumeServiceProtocol
from ..services.column_normalizer_service import (
    ColumnNormalizerService,
    ColumnNormalizerServiceProtocol,
)
from ..services.chat_service import ChatService, ChatServiceProtocol
from .repositories import (
    get_analytics_repository,
    get_auth_repository,
    get_candidates_repository,
    get_candidate_stage_comments_repository,
    get_custom_fields_repository,
    get_lookups_repository,
    get_import_repository,
    get_column_normalizer_repository,
    get_resume_repository,
)


def get_auth_service(
    auth_repo: AuthRepositoryProtocol = Depends(get_auth_repository),
) -> AuthServiceProtocol:
    return AuthService(auth_repo)


def get_analytics_service(
    analytics_repo: AnalyticsRepositoryProtocol = Depends(get_analytics_repository),
) -> AnalyticsServiceProtocol:
    return AnalyticsService(analytics_repo)


def get_resume_service(
    candidates_repo: CandidatesRepositoryProtocol = Depends(get_candidates_repository),
    resume_repo: ResumeRepositoryProtocol = Depends(get_resume_repository),
) -> ResumeServiceProtocol:
    return ResumeService(candidates_repo, resume_repo)


def get_candidate_service(
    candidates_repo: CandidatesRepositoryProtocol = Depends(get_candidates_repository),
    stage_comments_repo: CandidateStageCommentsRepositoryProtocol = Depends(
        get_candidate_stage_comments_repository
    ),
) -> CandidateServiceProtocol:
    return CandidateService(candidates_repo, stage_comments_repo)


def get_lookup_service(
    lookups_repo: LookupsRepositoryProtocol = Depends(get_lookups_repository),
) -> LookupServiceProtocol:
    return LookupService(lookups_repo)


def get_custom_field_type_service(
    custom_fields_repo: CustomFieldsRepositoryProtocol = Depends(get_custom_fields_repository),
    lookups_repo: LookupsRepositoryProtocol = Depends(get_lookups_repository),
) -> CustomFieldTypeServiceProtocol:
    return CustomFieldTypeService(custom_fields_repo, lookups_repo)


def get_column_normalizer_service(
    repo: ColumnNormalizerRepositoryProtocol = Depends(get_column_normalizer_repository),
) -> ColumnNormalizerServiceProtocol:
    return ColumnNormalizerService(repo)


def get_import_service(
    import_repo: ImportRepositoryProtocol = Depends(get_import_repository),
    lookup_service: LookupServiceProtocol = Depends(get_lookup_service),
    custom_field_type_service: CustomFieldTypeServiceProtocol = Depends(
        get_custom_field_type_service
    ),
    column_normalizer_service: ColumnNormalizerServiceProtocol = Depends(
        get_column_normalizer_service
    ),
) -> ImportServiceProtocol:
    return ImportService(
        import_repo=import_repo,
        lookup_service=lookup_service,
        custom_field_type_service=custom_field_type_service,
        column_normalizer_service=column_normalizer_service,
    )


def get_chat_service(
    candidate_service: CandidateServiceProtocol = Depends(get_candidate_service),
) -> ChatServiceProtocol:
    return ChatService(candidate_service)
