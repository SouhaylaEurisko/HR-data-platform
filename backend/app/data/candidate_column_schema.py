"""
Single source of truth: DB column key, human label, and header aliases for import mapping.
"""

from typing import Dict, List, TypedDict


class ColumnSchemaEntry(TypedDict):
    label: str
    aliases: List[str]


COLUMN_SCHEMA: Dict[str, ColumnSchemaEntry] = {
    "full_name": {
        "label": "Full Name",
        "aliases": [
            "full name", "fullname", "name", "first name", "last name",
            "given name", "family name", "surname",
            "candidate name", "applicant name",
        ],
    },
    "email": {
        "label": "Email",
        "aliases": [
            "email", "e-mail", "email address", "e mail", "mail",
        ],
    },
    "date_of_birth": {
        "label": "Date of Birth",
        "aliases": [
            "date of birth", "dob", "birth date", "birthday",
            "date of birth (dd/mm/yyyy)",
        ],
    },
    "nationality": {
        "label": "Nationality",
        "aliases": [
            "nationality", "country of origin", "country",
            "country of residence",
        ],
    },
    "current_address": {
        "label": "Current Address",
        "aliases": [
            "current address", "address", "location", "city",
            "current location", "current residence",
        ],
    },
    "residency_type_id": {
        "label": "Residency Type",
        "aliases": [
            "residency type", "residency", "visa status",
            "residency status", "legal status",
        ],
    },
    "marital_status_id": {
        "label": "Marital Status",
        "aliases": ["marital status", "married", "marital"],
    },
    "number_of_dependents": {
        "label": "Number of Dependents",
        "aliases": [
            "number of dependents", "dependents", "kids",
            "number of kids", "children",
        ],
    },
    "religion_sect": {
        "label": "Religion / Sect",
        "aliases": ["religion sect", "sect", "denomination"],
    },
    "passport_validity_status_id": {
        "label": "Passport Validity",
        "aliases": [
            "passport validity", "passport status", "passport",
            "passport valid",
        ],
    },
    "has_transportation": {
        "label": "Has Transportation",
        "aliases": [
            "has transportation", "transportation", "transport",
            "own vehicle", "car", "has car", "is motorized",
            "transportation availability",
        ],
    },
    "applied_position": {
        "label": "Applied Position",
        "aliases": [
            "applied position", "position", "job title", "role",
            "position applying for", "applied for position",
            "applied position location", "job",
        ],
    },
    "applied_position_location": {
        "label": "Position Location",
        "aliases": [
            "applied position location", "job location",
            "position location", "work location",
        ],
    },
    "is_open_for_relocation": {
        "label": "Open for Relocation",
        "aliases": [
            "open for relocation", "relocation", "willing to relocate",
            "open for reallocation",
            "for missions only", "missions only",
        ],
    },
    "years_of_experience": {
        "label": "Years of Experience",
        "aliases": [
            "years of experience", "experience", "yrs of experience",
            "total experience", "years experience", "yoe",
            "total years of experience",
            "in total, how many years of experience do you have?",
            "total experience (years)",
        ],
    },
    "is_employed": {
        "label": "Is Employed",
        "aliases": [
            "are you employed?", "employment status", "currently employed",
            "employed", "employed?",
        ],
    },
    "current_salary": {
        "label": "Current Salary",
        "aliases": [
            "current salary", "salary", "current salary expectations",
        ],
    },
    "expected_salary_remote": {
        "label": "Expected Salary (Remote)",
        "aliases": [
            "expected salary remote", "expected salary (remote)", "remote salary",
            "salary expectations remote",
        ],
    },
    "expected_salary_onsite": {
        "label": "Expected Salary (Onsite)",
        "aliases": [
            "expected salary onsite",
            "expected salary (onsite)",
            "onsite salary",
            "salary expectations onsite",
            "expected salary",
            "salary expectations",
            "salary expectation",
            "desired salary",
            "expected compensation",
        ],
    },
    "notice_period": {
        "label": "Notice Period",
        "aliases": [
            "notice period", "notice period (days)",
            "notice period (weeks)", "notice period (months)",
            "availability", "when can you start?",
        ],
    },
    "is_overtime_flexible": {
        "label": "Overtime Flexible",
        "aliases": [
            "overtime flexible", "overtime", "willing to work overtime",
        ],
    },
    "is_contract_flexible": {
        "label": "Contract Flexible",
        "aliases": [
            "contract flexible", "contractual flexibility",
            "contractual position flexibility",
        ],
    },
    "workplace_type_id": {
        "label": "Workplace Type",
        "aliases": [
            "workplace type", "work place type", "work type",
            "wfh", "remote/onsite", "work model",
        ],
    },
    "employment_type_id": {
        "label": "Employment Type",
        "aliases": ["employment type", "job type", "full time/part time"],
    },
    "tech_stack": {
        "label": "Tech Stack / Skills",
        "aliases": [
            "tech stack", "skills", "technologies", "programming languages",
            "technical skills",
        ],
    },
    "education_level_id": {
        "label": "Education Level",
        "aliases": [
            "education level", "educational level", "degree",
            "highest education", "qualification",
        ],
    },
    "education_completion_status_id": {
        "label": "Education Completion Status",
        "aliases": [
            "education completion", "educational completion",
            "degree status", "education status",
        ],
    },
    "applied_at": {
        "label": "Application Date",
        "aliases": [
            "applied at", "application date", "timestamp",
            "date applied", "submission date",
        ],
    },
}

ALL_KNOWN_COLUMNS = list(COLUMN_SCHEMA.keys())
COLUMN_LABELS: Dict[str, str] = {k: v["label"] for k, v in COLUMN_SCHEMA.items()}


def build_alias_reverse_index() -> Dict[str, str]:
    """Lowercase alias or column name → canonical DB column key."""
    rev: Dict[str, str] = {}
    for col, entry in COLUMN_SCHEMA.items():
        rev[col.lower()] = col
        for alias in entry["aliases"]:
            rev[alias.lower()] = col
    return rev
