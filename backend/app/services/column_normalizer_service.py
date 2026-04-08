"""
Column normalization service — maps messy Excel headers to known DB columns.

Two-tier approach:
  1. Programmatic: exact, case-insensitive, and alias matching.
  2. LLM fallback: single OpenAI call for remaining unmatched headers.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict, cast

from sqlalchemy.orm import Session

from ..data.candidate_column_schema import (
    ALL_KNOWN_COLUMNS,
    COLUMN_LABELS,
    build_alias_reverse_index,
)
from ..models.custom_field import CustomFieldDefinition
from ..prompts.column_normalizer_prompts import COLUMN_MAPPING_SYSTEM_PROMPT
from ..repository import column_normalizer_repository
from ..clients.llm_client import call_llm


logger = logging.getLogger(__name__)

# Re-export for import_service and callers
__all__ = [
    "ALL_KNOWN_COLUMNS",
    "COLUMN_LABELS",
    "ColumnMapping",
    "NormalizationResult",
    "get_available_columns",
    "match_programmatic",
    "normalize_columns",
]

# LLM confidence routing
LLM_DEFAULT_CONFIDENCE = 0.5
LLM_AUTO_MATCH_MIN = 0.90
LLM_SUGGEST_MIN = 0.70

_REVERSE_INDEX = build_alias_reverse_index()


class LlmColumnSuggestion(TypedDict, total=False):
    column: Optional[str]
    confidence: float


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


def _custom_header_to_field_key(defs: List[CustomFieldDefinition]) -> Dict[str, str]:
    """{label_lower | field_key_lower: field_key}."""
    m: Dict[str, str] = {}
    for d in defs:
        m[d.label.lower()] = d.field_key
        m[d.field_key.lower()] = d.field_key
    return m


def get_available_columns(db: Session, org_id: int) -> List[Dict[str, str]]:
    """Return list of available target columns with human-readable labels."""
    cols = [
        {"value": col, "label": COLUMN_LABELS.get(col, col)}
        for col in ALL_KNOWN_COLUMNS
    ]
    for d in column_normalizer_repository.fetch_active_custom_field_definitions(db, org_id):
        cols.append({"value": f"custom:{d.field_key}", "label": f"{d.label} (custom)"})
    return cols


def match_programmatic(headers: List[str]) -> NormalizationResult:
    """Match headers using exact/case-insensitive/alias matching."""
    result = NormalizationResult()
    for header in headers:
        cleaned = header.strip().lower()
        db_col = _REVERSE_INDEX.get(cleaned)
        if db_col:
            result.matched.append(
                ColumnMapping(
                    excel_header=header,
                    db_column=db_col,
                    confidence=1.0,
                    source="programmatic",
                )
            )
        else:
            result.unmatched.append(ColumnMapping(excel_header=header))
    return result


def _apply_custom_field_matches(
    result: NormalizationResult, header_to_field_key: Dict[str, str]
) -> None:
    """Move unmatched headers that match custom field label/key into matched."""
    still_unmatched: List[ColumnMapping] = []
    for mapping in result.unmatched:
        cleaned = mapping.excel_header.strip().lower()
        cf_key = header_to_field_key.get(cleaned)
        if cf_key:
            mapping.db_column = f"custom:{cf_key}"
            mapping.confidence = 1.0
            mapping.source = "programmatic"
            result.matched.append(mapping)
        else:
            still_unmatched.append(mapping)
    result.unmatched = still_unmatched


def _index_llm_mappings(raw: Dict[str, Any]) -> Dict[str, LlmColumnSuggestion]:
    """
    Normalize LLM response keys (strip + lower) so we match despite minor formatting.
    """
    out: Dict[str, LlmColumnSuggestion] = {}
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        norm = key.strip().lower()
        out[norm] = cast(LlmColumnSuggestion, val)
    return out


def _apply_llm_suggestions(
    result: NormalizationResult,
    suggestions_by_header: Dict[str, LlmColumnSuggestion],
) -> None:
    new_unmatched: List[ColumnMapping] = []
    for mapping in result.unmatched:
        suggestion = suggestions_by_header.get(mapping.excel_header.strip().lower())
        col = suggestion.get("column") if suggestion else None
        if col:
            mapping.db_column = col
            mapping.confidence = float(
                suggestion.get("confidence", LLM_DEFAULT_CONFIDENCE)
            )
            mapping.source = "llm"
            if mapping.confidence >= LLM_AUTO_MATCH_MIN:
                result.matched.append(mapping)
            elif mapping.confidence >= LLM_SUGGEST_MIN:
                result.suggested.append(mapping)
            else:
                new_unmatched.append(mapping)
        else:
            new_unmatched.append(mapping)
    result.unmatched = new_unmatched


async def _llm_suggest_mappings(
    unmatched_headers: List[str],
    custom_field_keys: List[str],
) -> Optional[Dict[str, LlmColumnSuggestion]]:
    """Single LLM call; returns mappings keyed by excel header (any casing)."""
    all_columns = ALL_KNOWN_COLUMNS.copy()
    all_columns.extend(f"custom:{k}" for k in custom_field_keys)

    user_msg = (
        f"Unmatched Excel headers:\n{unmatched_headers}\n\n"
        f"Known database columns:\n{all_columns}"
    )

    response = await call_llm(COLUMN_MAPPING_SYSTEM_PROMPT, user_msg)
    if not response or "mappings" not in response:
        return None
    raw = response["mappings"]
    if not isinstance(raw, dict):
        return None
    return _index_llm_mappings(raw)


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
    defs = column_normalizer_repository.fetch_active_custom_field_definitions(db, org_id)
    header_to_field_key = _custom_header_to_field_key(defs)
    custom_keys_unique = list({d.field_key for d in defs})

    result = match_programmatic(headers)
    _apply_custom_field_matches(result, header_to_field_key)

    if result.unmatched and use_llm:
        unmatched_headers = [m.excel_header for m in result.unmatched]
        indexed = await _llm_suggest_mappings(unmatched_headers, custom_keys_unique)
        if indexed:
            _apply_llm_suggestions(result, indexed)

    return result
