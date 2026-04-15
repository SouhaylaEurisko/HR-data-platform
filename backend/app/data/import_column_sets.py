"""
Import pipeline: lookup map, typed column sets, and application-table keys.

Used by ``import_service._map_row`` and ``_split_profile_and_application``.
"""

# Lookup columns requiring ID resolution (Excel text → lookup_option.id)
LOOKUP_COLUMN_MAP = {
    "residency_type_id": "residency_type",
    "marital_status_id": "marital_status",
    "passport_validity_status_id": "passport_validity",
    "workplace_type_id": "workplace_type",
    "employment_type_id": "employment_type",
    "education_level_id": "education_level",
    "education_completion_status_id": "education_completion",
}

BOOLEAN_COLUMNS = {
    "is_overtime_flexible",
    "is_contract_flexible",
    "is_employed",
}

DECIMAL_COLUMNS = {
    "current_salary",
    "expected_salary_remote",
    "expected_salary_onsite",
    "years_of_experience",
}

INT_COLUMNS = {
    "number_of_dependents",
}

DATE_COLUMNS = {"date_of_birth"}

STRING_COLUMNS = {
    "full_name",
    "email",
    "current_address",
    "religion_sect",
    "applied_position",
    "applied_position_location",
    "notice_period",
}

# Keys routed to Application (not CandidateProfile) when splitting import row kwargs
APPLICATION_IMPORT_KEYS = frozenset(
    {
        "import_session_id",
        "notice_period",
        "applied_at",
        "current_address",
        "nationality",
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
        "current_salary",
        "expected_salary_remote",
        "expected_salary_onsite",
        "is_overtime_flexible",
        "is_contract_flexible",
        "workplace_type_id",
        "employment_type_id",
        "is_employed",
        "tech_stack",
        "education_level_id",
        "education_completion_status_id",
    }
)
