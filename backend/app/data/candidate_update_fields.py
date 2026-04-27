"""
Which CandidateUpdate JSON keys map to ORM columns on CandidateProfile vs Application.

Used by candidate_service when splitting a PATCH body before persistence.
"""

PROFILE_UPDATE_KEYS = frozenset({"full_name", "email", "date_of_birth"})

APPLICATION_UPDATE_KEYS = frozenset(
    {
        "nationality",
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

# ``*_id`` foreign-key field on Application → matching ``*_label`` field exposed
# in CandidateRead / CandidateProfilePatchResponse. Used to resolve the human-
# readable label for the dropdown's selected lookup option.
LOOKUP_ID_TO_LABEL_KEYS: dict[str, str] = {
    "residency_type_id": "residency_type_label",
    "marital_status_id": "marital_status_label",
    "passport_validity_status_id": "passport_validity_status_label",
    "workplace_type_id": "workplace_type_label",
    "employment_type_id": "employment_type_label",
    "education_level_id": "education_level_label",
    "education_completion_status_id": "education_completion_status_label",
}
