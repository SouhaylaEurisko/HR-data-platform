"""Defaults for custom-column type detection (boolean hints, date formats)."""

from typing import FrozenSet, Tuple

# Values treated as boolean-like when ≥85% of sample matches
BOOLEAN_HINT_VALUES: FrozenSet[str] = frozenset({
    "yes", "no", "true", "false", "1", "0",
    "y", "n", "t", "f", "oui", "non",
})

# Tried in order for _is_date
DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
)
