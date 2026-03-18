"""
Type detection — infer custom field type from Excel column samples; create definitions + lookup data.
"""

import re
from datetime import datetime
from typing import Any, List, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from ..data.type_detection_defaults import BOOLEAN_HINT_VALUES, DATE_FORMATS
from ..models.custom_field import CustomFieldDefinition
from ..models.lookup import LookupCategory, LookupOption

FieldType = Literal["number", "date", "boolean", "lookup", "text"]

SAMPLE_MAX = 100
TYPE_MATCH_RATIO = 0.85
LOOKUP_CARDINALITY_MAX_RATIO = 0.1
LOOKUP_MAX_DISTINCT = 20
MAX_LOOKUP_OPTIONS = 50


def _non_empty_strings(values: List[Any]) -> List[str]:
    return [str(v).strip() for v in values if v is not None and str(v).strip()]


def _is_number(value: str) -> bool:
    cleaned = re.sub(r"[,$\s]", "", value.strip())
    if not cleaned:
        return False
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        return False


def _is_boolean(value: str) -> bool:
    return value.strip().lower() in BOOLEAN_HINT_VALUES


def detect_field_type(values: List[Any]) -> FieldType:
    """
    Infer field type from a sample of column values.

    Returns: number | date | boolean | lookup | text
    """
    non_empty = _non_empty_strings(values)
    if not non_empty:
        return "text"

    sample = non_empty[:SAMPLE_MAX]
    total = len(sample)

    num_count = sum(1 for v in sample if _is_number(v))
    if num_count / total >= TYPE_MATCH_RATIO:
        return "number"

    date_count = sum(1 for v in sample if _is_date(v))
    if date_count / total >= TYPE_MATCH_RATIO:
        return "date"

    bool_count = sum(1 for v in sample if _is_boolean(v))
    if bool_count / total >= TYPE_MATCH_RATIO:
        return "boolean"

    unique_values = {v.lower() for v in sample}
    cardinality_ratio = len(unique_values) / total
    if cardinality_ratio < LOOKUP_CARDINALITY_MAX_RATIO and len(unique_values) <= LOOKUP_MAX_DISTINCT:
        return "lookup"

    return "text"


def _to_snake_case(s: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", s.strip().lower())
    return re.sub(r"\s+", "_", cleaned)


def _create_lookup_for_custom_field(
    db: Session,
    org_id: int,
    field_key: str,
    label: str,
    values: List[Any],
) -> Tuple[Optional[int], Optional[LookupCategory]]:
    """Create LookupCategory + options for a lookup-type custom field."""
    non_empty = _non_empty_strings(values)
    unique_vals = sorted({v.strip() for v in non_empty})

    cat_code = f"custom_{field_key}"
    lookup_category = LookupCategory(
        code=cat_code,
        label=label,
        description=f"Auto-detected lookup for custom field '{label}'",
        is_system=False,
    )
    db.add(lookup_category)
    db.flush()

    for i, val in enumerate(unique_vals[:MAX_LOOKUP_OPTIONS], start=1):
        opt_code = _to_snake_case(val)
        db.add(
            LookupOption(
                category_id=lookup_category.id,
                organization_id=org_id,
                code=opt_code,
                label=val,
                display_order=i,
                is_active=True,
            )
        )

    return lookup_category.id, lookup_category


def create_custom_field(
    db: Session,
    org_id: int,
    label: str,
    values: List[Any],
) -> Tuple[CustomFieldDefinition, Optional[LookupCategory]]:
    """
    Detect type, create CustomFieldDefinition, and optionally
    LookupCategory + LookupOptions when type is lookup.
    """
    field_type = detect_field_type(values)
    field_key = _to_snake_case(label)

    existing = (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, field_key=field_key)
        .first()
    )
    if existing:
        return existing, None

    lookup_category = None
    lookup_category_id = None

    if field_type == "lookup":
        lookup_category_id, lookup_category = _create_lookup_for_custom_field(
            db, org_id, field_key, label, values
        )

    cfd = CustomFieldDefinition(
        organization_id=org_id,
        field_key=field_key,
        label=label,
        field_type=field_type,
        lookup_category_id=lookup_category_id,
        is_required=False,
        is_active=True,
    )
    db.add(cfd)
    db.flush()

    return cfd, lookup_category
