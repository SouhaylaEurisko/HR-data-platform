"""
Infer custom field type from Excel column samples (no database access).
"""

import re
from datetime import datetime
from typing import Any, List, Literal

from .type_detection_defaults import BOOLEAN_HINT_VALUES, DATE_FORMATS

FieldType = Literal["number", "date", "boolean", "lookup", "text"]

SAMPLE_MAX = 100
TYPE_MATCH_RATIO = 0.85
LOOKUP_CARDINALITY_MAX_RATIO = 0.1
LOOKUP_MAX_DISTINCT = 20
MAX_LOOKUP_OPTIONS = 50


def non_empty_sample_strings(values: List[Any]) -> List[str]:
    return [str(v).strip() for v in values if v is not None and str(v).strip()]


def to_snake_case(s: str) -> str:
    """Normalize label or option text to a stable snake_case code."""
    cleaned = re.sub(r"[^\w\s]", "", s.strip().lower())
    return re.sub(r"\s+", "_", cleaned)


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
    non_empty = non_empty_sample_strings(values)
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
