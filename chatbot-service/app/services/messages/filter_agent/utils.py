"""Utilities for Filter Agent."""
from datetime import date, datetime
from typing import Any, Dict, List


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
            parts.append(f"Salary: ${row['expected_salary']:,.0f}")
        if row.get("current_address"):
            parts.append(f"Location: {row['current_address']}")
        lines.append(f"{i+1}. " + " | ".join(parts))

    text = "\n".join(lines)
    if len(rows) > max_rows:
        text += f"\n... and {len(rows) - max_rows} more candidates."
    return text


def sanitize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Make rows JSON-serializable (handle dates, etc.)."""
    clean = []
    for row in rows:
        r = {}
        for k, v in row.items():
            if isinstance(v, (datetime, date)):
                r[k] = v.isoformat()
            else:
                r[k] = v
        clean.append(r)
    return clean
