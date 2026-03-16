"""Utilities for Filter Agent."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ...utils.salary_parser import parse_salary_text

# Corrupt years_experience values above this threshold are capped / excluded
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
        if row.get("full_name"):
            parts.append(row["full_name"])
        if row.get("position"):
            parts.append(f"Position: {row['position']}")
        if row.get("nationality"):
            parts.append(f"Nationality: {row['nationality']}")
        if row.get("years_experience") is not None:
            parts.append(f"Experience: {row['years_experience']} yrs")
        if row.get("expected_salary") is not None:
            parts.append(f"Salary: ${float(row['expected_salary']):,.0f}")
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

        # Nullify corrupt experience values so the UI shows N/A
        # instead of "20240304000000 years"
        exp = r.get("years_experience")
        if exp is not None and exp > _MAX_REASONABLE_EXPERIENCE:
            r["years_experience"] = None

        clean.append(r)
    return clean


def filter_empty_rows(
    rows: List[Dict[str, Any]],
    required_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Remove rows where key candidate fields are all NULL / empty.

    When *required_field* is given (e.g. ``"years_experience"``), only
    rows that have a non-NULL value for that field are kept.  This is
    used when the query is explicitly about that field (e.g. "highest
    experience").
    """
    if required_field:
        return [
            r for r in rows
            if r.get(required_field) is not None
        ]

    # General case — keep rows that have at least a name or position
    return [
        r for r in rows
        if r.get("full_name") or r.get("position")
    ]


def resort_by_salary(
    rows: List[Dict[str, Any]],
    descending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Re-sort rows by the parsed ``expected_salary_text`` instead of the
    corrupt ``expected_salary`` FLOAT column.

    For each row the salary text is parsed into ``(min, max)``.
    When *descending* is True the rows are sorted by the **max** value
    (highest first); when False by the **min** value (lowest first).
    Rows without a parseable salary are pushed to the end.
    """

    def _sort_key(row: Dict[str, Any]):
        parsed = parse_salary_text(row.get("expected_salary_text"))
        if parsed is None:
            return float("-inf") if descending else float("inf")
        return parsed[1] if descending else parsed[0]

    return sorted(rows, key=_sort_key, reverse=descending)
