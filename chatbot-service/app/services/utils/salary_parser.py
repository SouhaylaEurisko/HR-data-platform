"""
Salary text parser — extracts numeric salary values from free-text strings.

The ``expected_salary`` FLOAT column in the database is unreliable because
raw salary strings like "1500$- 1800/2500" are naively parsed into a single
number by stripping all non-digit characters (giving 150018002500).

This module reads the **expected_salary_text** VARCHAR column instead and
extracts meaningful min / max values from common formats:

  "2000"             →  (2000, 2000)
  "1500-2000"        →  (1500, 2000)
  "1500$- 1800/2500" →  (1500, 2500)
  "1,500 - 2,000$"   →  (1500, 2000)
  "AED 3000"         →  (3000, 3000)
  "2500 USD"         →  (2500, 2500)
  ""  / None         →  None
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Single-value parser ──────────────────────────────────────────────────────

def parse_salary_text(text: Any) -> Optional[Tuple[float, float]]:
    """
    Parse a salary text string and return ``(min_salary, max_salary)``.

    Handles ranges separated by ``-``, ``–``, ``/``, ``to`` and arbitrary
    currency symbols / whitespace.  If only a single number is found the
    result is ``(value, value)``.

    Returns ``None`` when no usable number can be extracted.
    """
    if text is None:
        return None

    raw = str(text).strip()
    if not raw:
        return None

    # Extract all number-like tokens (supports commas as thousands separators)
    # e.g. "1,500" → "1,500", "2500" → "2500", "1500.50" → "1500.50"
    tokens = re.findall(r"[\d]+(?:[,\.][\d]+)*", raw)

    if not tokens:
        return None

    parsed: List[float] = []
    for tok in tokens:
        try:
            # Decide if comma is thousands-sep or decimal-sep
            # "1,500" → 1500   "1,50" → 1.50 (European)   "1,500.00" → 1500.00
            if "," in tok and "." in tok:
                # Both present: comma is thousands, dot is decimal
                value = float(tok.replace(",", ""))
            elif "," in tok:
                parts = tok.split(",")
                if len(parts) == 2 and len(parts[1]) == 3:
                    # e.g. "1,500" — thousands separator
                    value = float(tok.replace(",", ""))
                elif len(parts) == 2 and len(parts[1]) <= 2:
                    # e.g. "1,50" — European decimal
                    value = float(tok.replace(",", "."))
                else:
                    # Multiple commas like "1,000,000" — thousands
                    value = float(tok.replace(",", ""))
            else:
                value = float(tok)

            if value > 0:
                parsed.append(value)
        except ValueError:
            continue

    if not parsed:
        return None

    return (min(parsed), max(parsed))


# ── Bulk statistics ──────────────────────────────────────────────────────────

def compute_salary_stats(salary_texts: List[Any]) -> Dict[str, Any]:
    """
    Compute salary statistics from a list of ``expected_salary_text`` values.

    Returns a dict like::

        {
            "count":          12,
            "min_salary":     1500.0,
            "max_salary":     5000.0,
            "avg_min_salary": 2100.0,
            "avg_max_salary": 3200.0,
        }

    Returns an empty dict when no values can be parsed.
    """
    all_mins: List[float] = []
    all_maxes: List[float] = []

    for text in salary_texts:
        result = parse_salary_text(text)
        if result:
            mn, mx = result
            all_mins.append(mn)
            all_maxes.append(mx)

    if not all_mins:
        return {}

    return {
        "count": len(all_mins),
        "min_salary": min(all_mins),
        "max_salary": max(all_maxes),
        "avg_min_salary": round(sum(all_mins) / len(all_mins), 2),
        "avg_max_salary": round(sum(all_maxes) / len(all_maxes), 2),
    }
