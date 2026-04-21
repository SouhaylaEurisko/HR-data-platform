"""Heuristics for filter+aggregation query shape (e.g. count-only, no sample rows)."""
import re
from typing import Any, Dict, List, Optional

# User wants a count / size, not a list of people.
_COUNT_HINT = re.compile(
    r"\b("
    r"how\s+many|"
    r"what\s+is\s+the\s+total|what'?s\s+the\s+total|"
    r"total\s+count|"
    r"number\s+of\s+(them|those|these|people|candidates|applicants|us)|"
    r"how\s+many\s+are\s+(there|they)|"
    r"how\s+many\s+do\s+we\s+have|"
    r"in\s+total|"
    r"count\s+of|"
    r"give\s+me\s+the\s+count|"
    r"what\s+is\s+the\s+count|what'?s\s+the\s+count"
    r")\b",
    re.IGNORECASE,
)

# Explicitly asking to see people / names — keep sample rows.
_LIST_HINT = re.compile(
    r"\b("
    r"show\s+me|"
    r"list|"
    r"display|"
    r"who\s+(are|is)|"
    r"\bnames?\b|"
    r"some\s+candidates|"
    r"examples?|"
    r"\bsample\b|"
    r"top\s+\d+|"
    r"first\s+\d+"
    r")\b",
    re.IGNORECASE,
)


def is_count_only_query(message: str) -> bool:
    """
    True when the user is asking for a total count / size, not for a roster or sample rows.
    """
    text = (message or "").strip()
    if not text:
        return False
    if _LIST_HINT.search(text):
        return False
    return bool(_COUNT_HINT.search(text))


def total_candidates_from_stats(stats: List[Dict[str, Any]]) -> Optional[int]:
    """Read total_candidates from aggregation (one row, or sum when grouped)."""
    vals: List[int] = []
    for row in stats:
        v = row.get("total_candidates")
        if v is None:
            continue
        try:
            vals.append(int(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return vals[0] if len(vals) == 1 else sum(vals)
