"""Map Excel rows to CandidateProfile / Application kwargs for import."""

from datetime import datetime
from typing import Any, Dict

from ..data.import_column_sets import (
    APPLICATION_IMPORT_KEYS,
    BOOLEAN_COLUMNS,
    DATE_COLUMNS,
    DECIMAL_COLUMNS,
    INT_COLUMNS,
    LOOKUP_COLUMN_MAP,
    STRING_COLUMNS,
)
from ..services.lookup_service import LookupServiceProtocol
from .import_row_converters import (
    to_bool_or_none,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
    to_json_safe,
    to_relocation_openness_or_none,
    to_transportation_availability_or_none,
    truncate,
)

def split_profile_and_application(mapped: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Split flat row kwargs (legacy candidate-shaped) into CandidateProfile and Application dicts.
    Nationality is stored on ``applications.nationality`` (not custom_fields).
    """
    profile: Dict[str, Any] = {
        "organization_id": mapped["organization_id"],
        "import_session_id": mapped["import_session_id"],
    }
    for k in ("full_name", "email", "date_of_birth"):
        if k in mapped:
            profile[k] = mapped[k]

    application: Dict[str, Any] = {"import_session_id": mapped["import_session_id"]}
    for k in APPLICATION_IMPORT_KEYS:
        if k == "import_session_id" or k not in mapped:
            continue
        application[k] = mapped[k]

    custom = dict(mapped.get("custom_fields") or {})
    if mapped.get("raw_import_data") is not None:
        custom["_raw_import_data"] = mapped["raw_import_data"]

    reserved_for_split = (
        set(profile.keys())
        | APPLICATION_IMPORT_KEYS
        | {"organization_id", "raw_import_data", "custom_fields"}
    )
    for k, v in mapped.items():
        if k in reserved_for_split:
            continue
        if v is not None:
            custom[k] = to_json_safe(v)

    application["custom_fields"] = custom
    return profile, application


def map_import_row(
    lookup_service: LookupServiceProtocol,
    row_data: Dict[str, Any],
    column_mappings: Dict[str, str],
    org_id: int,
) -> Dict[str, Any]:
    """Map one Excel row dict to flat candidate-shaped kwargs (before split_profile_and_application)."""
    candidate_kwargs: Dict[str, Any] = {}
    custom_fields: Dict[str, Any] = {}
    raw_import_data = {k: to_json_safe(v) for k, v in row_data.items()}

    for excel_header, raw_value in row_data.items():
        header_lower = excel_header.strip().lower()
        db_col = column_mappings.get(header_lower)
        if not db_col:
            continue

        if db_col.startswith("custom:"):
            cf_key = db_col[len("custom:") :]
            custom_fields[cf_key] = to_json_safe(raw_value)
            continue

        if db_col in LOOKUP_COLUMN_MAP:
            category_code = LOOKUP_COLUMN_MAP[db_col]
            resolved_id = lookup_service.resolve_lookup_value(
                category_code,
                org_id,
                str(raw_value) if raw_value else "",
            )
            if resolved_id:
                candidate_kwargs[db_col] = resolved_id
            continue

        if db_col == "is_open_for_relocation":
            val = to_relocation_openness_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col == "has_transportation":
            val = to_transportation_availability_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in BOOLEAN_COLUMNS:
            val = to_bool_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in DECIMAL_COLUMNS:
            val = to_decimal_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in INT_COLUMNS:
            val = to_int_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in DATE_COLUMNS:
            val = to_date_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col == "applied_at":
            if isinstance(raw_value, datetime):
                candidate_kwargs[db_col] = raw_value
            elif isinstance(raw_value, str):
                try:
                    candidate_kwargs[db_col] = datetime.fromisoformat(raw_value.strip())
                except ValueError:
                    pass
        elif db_col == "tech_stack":
            if isinstance(raw_value, str):
                candidate_kwargs[db_col] = [s.strip() for s in raw_value.split(",") if s.strip()]
            elif isinstance(raw_value, list):
                candidate_kwargs[db_col] = raw_value
        elif db_col == "email":
            email_str = str(raw_value).strip() if raw_value else ""
            if "@" in email_str and "." in email_str:
                candidate_kwargs[db_col] = truncate(email_str, 320)
        elif db_col == "nationality":
            if raw_value is not None and str(raw_value).strip():
                candidate_kwargs[db_col] = truncate(str(raw_value), 100)
        elif db_col in STRING_COLUMNS:
            if raw_value is not None and str(raw_value).strip():
                candidate_kwargs[db_col] = truncate(str(raw_value), 255)

    candidate_kwargs["custom_fields"] = custom_fields if custom_fields else {}
    candidate_kwargs["raw_import_data"] = raw_import_data
    return candidate_kwargs
