"""
Type detection service — auto-detects field types from column data
when HR creates a new custom field from an unmatched Excel column.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.custom_field import CustomFieldDefinition
from ..models.lookup import LookupCategory, LookupOption


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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
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


_BOOLEAN_VALUES = {
    "yes", "no", "true", "false", "1", "0",
    "y", "n", "t", "f", "oui", "non",
}


def _is_boolean(value: str) -> bool:
    return value.strip().lower() in _BOOLEAN_VALUES


def detect_field_type(values: List[Any]) -> str:
    """
    Detect the best field type from a sample of column values.

    Returns one of: 'number', 'date', 'boolean', 'lookup', 'text'
    """
    non_empty = [str(v).strip() for v in values if v is not None and str(v).strip()]
    if not non_empty:
        return "text"

    sample = non_empty[:100]
    total = len(sample)

    num_count = sum(1 for v in sample if _is_number(v))
    if num_count / total >= 0.85:
        return "number"

    date_count = sum(1 for v in sample if _is_date(v))
    if date_count / total >= 0.85:
        return "date"

    bool_count = sum(1 for v in sample if _is_boolean(v))
    if bool_count / total >= 0.85:
        return "boolean"

    # Cardinality check for enum/lookup detection
    unique_values = set(v.lower() for v in sample)
    cardinality_ratio = len(unique_values) / total
    if cardinality_ratio < 0.1 and len(unique_values) <= 20:
        return "lookup"

    return "text"


def _to_snake_case(s: str) -> str:
    """Convert a display label to a snake_case key."""
    cleaned = re.sub(r"[^\w\s]", "", s.strip().lower())
    return re.sub(r"\s+", "_", cleaned)


def create_custom_field(
    db: Session,
    org_id: int,
    label: str,
    values: List[Any],
) -> Tuple[CustomFieldDefinition, Optional[LookupCategory]]:
    """
    Detect type, create CustomFieldDefinition, and optionally
    create a LookupCategory + LookupOptions if the type is 'lookup'.
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
        non_empty = [str(v).strip() for v in values if v is not None and str(v).strip()]
        unique_vals = sorted(set(v.strip() for v in non_empty))

        cat_code = f"custom_{field_key}"
        lookup_category = LookupCategory(
            code=cat_code,
            label=label,
            description=f"Auto-detected lookup for custom field '{label}'",
            is_system=False,
        )
        db.add(lookup_category)
        db.flush()
        lookup_category_id = lookup_category.id

        for i, val in enumerate(unique_vals[:50], start=1):
            opt_code = _to_snake_case(val)
            db.add(LookupOption(
                category_id=lookup_category.id,
                organization_id=org_id,
                code=opt_code,
                label=val,
                display_order=i,
                is_active=True,
            ))

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
