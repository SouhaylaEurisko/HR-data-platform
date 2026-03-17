"""
Column normalization service — maps messy Excel headers to known DB columns.

Two-tier approach:
  1. Programmatic: exact, case-insensitive, and alias matching.
  2. LLM fallback: single OpenAI call for remaining unmatched headers.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.custom_field import CustomFieldDefinition
from .column_normalizer_prompts import COLUMN_MAPPING_SYSTEM_PROMPT
from .llm_client import call_llm

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Known candidate columns + human-readable aliases
# ──────────────────────────────────────────────

CANDIDATE_COLUMNS: Dict[str, List[str]] = {
    "full_name": [
        "full name", "fullname", "name", "first name", "last name",
        "fname", "lname", "given name", "family name", "surname",
        "candidate name", "applicant name",
    ],
    "email": [
        "email", "e-mail", "email address", "e mail", "mail",
    ],
    "date_of_birth": [
        "date of birth", "dob", "birth date", "birthday",
        "date of birth (dd/mm/yyyy)",
    ],
    "nationality": [
        "nationality", "country of origin", "country",
        "country of residence",
    ],
    "current_address": [
        "current address", "address", "location", "city",
        "current location", "current residence",
    ],
    "residency_type_id": [
        "residency type", "residency", "visa status",
        "residency status", "legal status",
    ],
    "marital_status_id": [
        "marital status", "married", "marital",
    ],
    "number_of_dependents": [
        "number of dependents", "dependents", "kids",
        "number of kids", "children",
    ],
    "religion_sect": [
        "religion sect", "sect", "denomination",
    ],
    "passport_validity_status_id": [
        "passport validity", "passport status", "passport",
        "passport valid",
    ],
    "has_transportation": [
        "has transportation", "transportation", "transport",
        "own vehicle", "car", "has car",
    ],
    "applied_position": [
        "applied position", "position", "job title", "role",
        "position applying for", "applied for position",
        "applied position location", "job",
    ],
    "applied_position_location": [
        "applied position location", "job location",
        "position location", "work location",
    ],
    "is_open_for_relocation": [
        "open for relocation", "relocation", "willing to relocate",
        "open for reallocation",
    ],
    "years_of_experience": [
        "years of experience", "experience", "yrs of experience",
        "total experience", "years experience", "yoe",
        "total years of experience",
        "in total, how many years of experience do you have?",
        "total experience (years)",
    ],
    "is_employed": [
        "are you employed?", "employment status", "currently employed",
        "employed", "employed?",
    ],
    "current_salary": [
        "current salary", "salary", "current salary expectations",
    ],
    "expected_salary_remote": [
        "expected salary remote", "expected salary (remote)", "remote salary",
        "salary expectations remote",
    ],
    "expected_salary_onsite": [
        "expected salary onsite", "expected salary (onsite)", "onsite salary",
        "salary expectations onsite",
    ],
    "notice_period": [
        "notice period", "notice period (days)",
        "notice period (weeks)", "notice period (months)",
        "availability", "when can you start?",
    ],
    "is_overtime_flexible": [
        "overtime flexible", "overtime", "willing to work overtime",
    ],
    "is_contract_flexible": [
        "contract flexible", "contractual flexibility",
        "contractual position flexibility",
    ],
    "workplace_type_id": [
        "workplace type", "work place type", "work type",
        "wfh", "remote/onsite", "work model",
    ],
    "employment_type_id": [
        "employment type", "job type", "full time/part time",
    ],
    "tech_stack": [
        "tech stack", "skills", "technologies", "programming languages",
        "technical skills",
    ],
    "education_level_id": [
        "education level", "educational level", "degree",
        "highest education", "qualification",
    ],
    "education_completion_status_id": [
        "education completion", "educational completion",
        "degree status", "education status",
    ],
    "applied_at": [
        "applied at", "application date", "timestamp",
        "date applied", "submission date",
    ],
}

ALL_KNOWN_COLUMNS = list(CANDIDATE_COLUMNS.keys())

COLUMN_LABELS: Dict[str, str] = {
    "full_name": "Full Name",
    "email": "Email",
    "date_of_birth": "Date of Birth",
    "nationality": "Nationality",
    "current_address": "Current Address",
    "residency_type_id": "Residency Type",
    "marital_status_id": "Marital Status",
    "number_of_dependents": "Number of Dependents",
    "religion_sect": "Religion / Sect",
    "passport_validity_status_id": "Passport Validity",
    "has_transportation": "Has Transportation",
    "applied_position": "Applied Position",
    "applied_position_location": "Position Location",
    "is_open_for_relocation": "Open for Relocation",
    "years_of_experience": "Years of Experience",
    "is_employed": "Is Employed",
    "current_salary": "Current Salary",
    "expected_salary_remote": "Expected Salary (Remote)",
    "expected_salary_onsite": "Expected Salary (Onsite)",
    "notice_period": "Notice Period",
    "is_overtime_flexible": "Overtime Flexible",
    "is_contract_flexible": "Contract Flexible",
    "workplace_type_id": "Workplace Type",
    "employment_type_id": "Employment Type",
    "tech_stack": "Tech Stack / Skills",
    "education_level_id": "Education Level",
    "education_completion_status_id": "Education Completion Status",
    "applied_at": "Application Date",
}


def get_available_columns(db: Session, org_id: int) -> List[Dict[str, str]]:
    """Return list of available target columns with human-readable labels."""
    cols = [
        {"value": col, "label": COLUMN_LABELS.get(col, col)}
        for col in ALL_KNOWN_COLUMNS
    ]
    defs = (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, is_active=True)
        .all()
    )
    for d in defs:
        cols.append({"value": f"custom:{d.field_key}", "label": f"{d.label} (custom)"})
    return cols


@dataclass
class ColumnMapping:
    excel_header: str
    db_column: Optional[str] = None
    confidence: float = 0.0
    source: str = "unmatched"  # programmatic | llm | unmatched


@dataclass
class NormalizationResult:
    matched: List[ColumnMapping] = field(default_factory=list)
    suggested: List[ColumnMapping] = field(default_factory=list)
    unmatched: List[ColumnMapping] = field(default_factory=list)


def _build_reverse_index() -> Dict[str, str]:
    """Build alias → db_column reverse lookup (all lowercase)."""
    rev = {}
    for col, aliases in CANDIDATE_COLUMNS.items():
        rev[col.lower()] = col
        for alias in aliases:
            rev[alias.lower()] = col
    return rev


_REVERSE_INDEX = _build_reverse_index()


def match_programmatic(headers: List[str]) -> NormalizationResult:
    """Match headers using exact/case-insensitive/alias matching."""
    result = NormalizationResult()
    for header in headers:
        cleaned = header.strip().lower()
        db_col = _REVERSE_INDEX.get(cleaned)
        if db_col:
            result.matched.append(ColumnMapping(
                excel_header=header,
                db_column=db_col,
                confidence=1.0,
                source="programmatic",
            ))
        else:
            result.unmatched.append(ColumnMapping(excel_header=header))
    return result


def _get_custom_field_columns(db: Session, org_id: int) -> Dict[str, str]:
    """Return {label_lower: field_key} for org's custom field definitions."""
    defs = (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, is_active=True)
        .all()
    )
    mapping = {}
    for d in defs:
        mapping[d.label.lower()] = d.field_key
        mapping[d.field_key.lower()] = d.field_key
    return mapping


async def normalize_columns(
    headers: List[str],
    db: Session,
    org_id: int,
    use_llm: bool = True,
) -> NormalizationResult:
    """
    Full normalization pipeline:
      1. Programmatic matching against known columns + custom field defs.
      2. LLM fallback for remaining unmatched headers.
    """
    # Step 1: programmatic
    result = match_programmatic(headers)

    # Also check custom field definitions
    custom_cols = _get_custom_field_columns(db, org_id)
    still_unmatched = []
    for mapping in result.unmatched:
        cleaned = mapping.excel_header.strip().lower()
        cf_key = custom_cols.get(cleaned)
        if cf_key:
            mapping.db_column = f"custom:{cf_key}"
            mapping.confidence = 1.0
            mapping.source = "programmatic"
            result.matched.append(mapping)
        else:
            still_unmatched.append(mapping)
    result.unmatched = still_unmatched

    # Step 2: LLM fallback
    if result.unmatched and use_llm:
        unmatched_headers = [m.excel_header for m in result.unmatched]
        llm_suggestions = await _llm_suggest_mappings(unmatched_headers, custom_cols)

        if llm_suggestions:
            new_unmatched = []
            for mapping in result.unmatched:
                suggestion = llm_suggestions.get(mapping.excel_header)
                if suggestion and suggestion.get("column"):
                    mapping.db_column = suggestion["column"]
                    mapping.confidence = float(suggestion.get("confidence", 0.5))
                    mapping.source = "llm"
                    if mapping.confidence >= 0.90:
                        result.matched.append(mapping)
                    elif mapping.confidence >= 0.70:
                        result.suggested.append(mapping)
                    else:
                        new_unmatched.append(mapping)
                else:
                    new_unmatched.append(mapping)
            result.unmatched = new_unmatched

    return result


async def _llm_suggest_mappings(
    unmatched_headers: List[str],
    custom_field_cols: Dict[str, str],
) -> Optional[Dict]:
    """Single LLM call to suggest mappings for unmatched headers."""
    all_columns = ALL_KNOWN_COLUMNS.copy()
    for key in custom_field_cols.values():
        all_columns.append(f"custom:{key}")

    user_msg = (
        f"Unmatched Excel headers:\n{unmatched_headers}\n\n"
        f"Known database columns:\n{all_columns}"
    )

    response = await call_llm(COLUMN_MAPPING_SYSTEM_PROMPT, user_msg)
    if response and "mappings" in response:
        return response["mappings"]
    return None
