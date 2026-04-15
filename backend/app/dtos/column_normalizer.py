"""Column import normalization DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


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
