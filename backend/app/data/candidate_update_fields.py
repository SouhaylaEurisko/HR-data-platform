"""
Which CandidateUpdate JSON keys map to ORM columns on CandidateProfile vs Application.

Used by candidate_service when splitting a PATCH body before persistence.
"""

PROFILE_UPDATE_KEYS = frozenset({"full_name", "email", "date_of_birth"})

APPLICATION_UPDATE_KEYS = frozenset(
    {
        "current_address",
        "residency_type_id",
        "marital_status_id",
        "number_of_dependents",
        "religion_sect",
        "passport_validity_status_id",
        "has_transportation",
        "applied_position",
        "applied_position_location",
        "is_open_for_relocation",
        "years_of_experience",
        "is_employed",
        "current_salary",
        "expected_salary_remote",
        "expected_salary_onsite",
        "notice_period",
        "is_overtime_flexible",
        "is_contract_flexible",
        "workplace_type_id",
        "employment_type_id",
        "tech_stack",
        "education_level_id",
        "education_completion_status_id",
    }
)
