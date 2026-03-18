"""Utilities for Aggregation Agent."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List


def stats_to_display(rows: List[Dict[str, Any]]) -> str:
    """Format aggregation result rows for the LLM summariser."""
    if not rows:
        return "No statistics available."

    lines = []
    for row in rows:
        parts = []
        for k, v in row.items():
            if v is not None:
                if isinstance(v, (float, Decimal)):
                    parts.append(f"{k}: {float(v):,.2f}")
                else:
                    parts.append(f"{k}: {v}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def sanitize_stats(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Make stats JSON-serializable (handle dates, Decimals, etc.)."""
    clean = []
    for row in rows:
        r = {}
        for k, v in row.items():
            if isinstance(v, (datetime, date)):
                r[k] = v.isoformat()
            elif isinstance(v, Decimal):
                r[k] = round(float(v), 2)
            elif isinstance(v, float):
                r[k] = round(v, 2)
            else:
                r[k] = v
        clean.append(r)
    return clean
