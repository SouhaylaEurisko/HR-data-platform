"""Assemble CandidateRead from ORM profile, application, and related context."""

from typing import Any, Mapping, Optional

from ..data.candidate_update_fields import LOOKUP_ID_TO_LABEL_KEYS
from ..dtos.hr_stage_comments import HrStageCommentsRead
from ..models.candidates import CandidateProfile
from ..schemas.candidate import CandidateRead, RelatedApplicationSummary
from .candidate_fields import (
    optional_application_status,
    resolved_nationality_from_application,
    transport_enum_from_value,
)


def build_candidate_read(
    *,
    candidate: CandidateProfile,
    application: Any,
    import_filename: Optional[str],
    import_sheet: Optional[str],
    related: list[RelatedApplicationSummary],
    hr_comments: HrStageCommentsRead,
    application_status_raw: Optional[str],
    application_index: Optional[int],
    application_total: Optional[int],
    lookup_labels_by_option_id: Optional[Mapping[int, str]] = None,
) -> CandidateRead:
    nationality = resolved_nationality_from_application(application)
    app_cf: dict = dict(application.custom_fields or {}) if application else {}
    raw_import_data = app_cf.pop("_raw_import_data", None)
    app_cf.pop("nationality", None)

    label_kwargs: dict[str, Optional[str]] = {}
    if lookup_labels_by_option_id is not None:
        for id_field, label_field in LOOKUP_ID_TO_LABEL_KEYS.items():
            option_id = getattr(application, id_field, None) if application else None
            label_kwargs[label_field] = (
                lookup_labels_by_option_id.get(option_id) if option_id is not None else None
            )

    return CandidateRead(
        id=candidate.id,
        organization_id=candidate.organization_id,
        import_session_id=candidate.import_session_id,
        applied_at=application.applied_at if application else None,
        full_name=candidate.full_name,
        email=candidate.email,
        date_of_birth=candidate.date_of_birth,
        nationality=nationality,
        current_address=application.current_address if application else None,
        residency_type_id=application.residency_type_id if application else None,
        marital_status_id=application.marital_status_id if application else None,
        number_of_dependents=application.number_of_dependents if application else None,
        religion_sect=application.religion_sect if application else None,
        passport_validity_status_id=application.passport_validity_status_id if application else None,
        has_transportation=transport_enum_from_value(
            application.has_transportation if application else None
        ),
        applied_position=application.applied_position if application else None,
        applied_position_location=application.applied_position_location if application else None,
        is_open_for_relocation=application.is_open_for_relocation if application else None,
        years_of_experience=application.years_of_experience if application else None,
        is_employed=application.is_employed if application else None,
        current_salary=application.current_salary if application else None,
        expected_salary_remote=application.expected_salary_remote if application else None,
        expected_salary_onsite=application.expected_salary_onsite if application else None,
        notice_period=application.notice_period if application else None,
        is_overtime_flexible=application.is_overtime_flexible if application else None,
        is_contract_flexible=application.is_contract_flexible if application else None,
        workplace_type_id=application.workplace_type_id if application else None,
        employment_type_id=application.employment_type_id if application else None,
        tech_stack=(application.tech_stack or []) if application else [],
        education_level_id=application.education_level_id if application else None,
        education_completion_status_id=application.education_completion_status_id
        if application
        else None,
        custom_fields=app_cf,
        raw_import_data=raw_import_data,
        created_at=candidate.created_at,
        updated_at=(application.updated_at if application else candidate.created_at),
        hr_stage_comments=hr_comments,
        application_status=optional_application_status(application_status_raw),
        import_filename=import_filename,
        import_sheet=import_sheet,
        application_index=application_index,
        application_total=application_total,
        related_applications=related,
        **label_kwargs,
    )
