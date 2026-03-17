"""Utilities for Filter Agent."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

_MAX_REASONABLE_EXPERIENCE = 50


def rows_to_display(rows: List[Dict[str, Any]], max_rows: int = 10) -> str:
    """
    Convert query result rows to a compact text representation
    that can be sent to the LLM for summarisation.
    """
    if not rows:
        return "No candidates found."

    lines = []
    for i, row in enumerate(rows[:max_rows]):
        parts = []
        name = row.get("full_name")
        if name:
            parts.append(name)
        if row.get("applied_position"):
            parts.append(f"Position: {row['applied_position']}")
        if row.get("nationality"):
            parts.append(f"Nationality: {row['nationality']}")
        if row.get("years_of_experience") is not None:
            parts.append(f"Experience: {row['years_of_experience']} yrs")
        if row.get("current_salary") is not None:
            parts.append(f"Salary: ${float(row['current_salary']):,.0f}")
        if row.get("current_address"):
            parts.append(f"Location: {row['current_address']}")
        lines.append(f"{i+1}. " + " | ".join(parts))

    text = "\n".join(lines)
    if len(rows) > max_rows:
        text += f"\n... and {len(rows) - max_rows} more candidates."
    return text


def sanitize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Make rows JSON-serializable (handle dates, Decimals, etc.)."""
    clean = []
    for row in rows:
        r = {}
        for k, v in row.items():
            if isinstance(v, (datetime, date)):
                r[k] = v.isoformat()
            elif isinstance(v, Decimal):
                r[k] = float(v)
            else:
                r[k] = v

        exp = r.get("years_of_experience")
        if exp is not None and exp > _MAX_REASONABLE_EXPERIENCE:
            r["years_of_experience"] = None

        clean.append(r)
    return clean


def filter_empty_rows(
    rows: List[Dict[str, Any]],
    required_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if required_field:
        return [r for r in rows if r.get(required_field) is not None]
    return [
        r for r in rows
        if r.get("full_name") or r.get("applied_position")
    ]


def resort_by_salary(
    rows: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """Re-sort rows by current_salary."""
    def _sort_key(row: Dict[str, Any]):
        val = row.get("current_salary")
        if val is None:
            return float("-inf") if descending else float("inf")
        return float(val)
    return sorted(rows, key=_sort_key, reverse=descending)
