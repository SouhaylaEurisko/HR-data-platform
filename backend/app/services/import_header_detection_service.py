"""
XLSX header and multi-table detection for the import pipeline.

Isolated so heuristics (what counts as a header row vs data, gaps between tables)
can evolve without touching the rest of import mapping and persistence.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, List, Optional


def cell_looks_like_header_label(cell: Any) -> bool:
    """True if the cell value looks like a column title rather than data."""
    if cell is None:
        return False
    # Excel dates come as datetime; reject them
    if isinstance(cell, (datetime, date)):
        return False
    s = str(cell).strip()
    if not s:
        return False
    # Data-like: contains @ (email), or is mostly digits, or looks like a date/number
    if "@" in s:
        return False
    if len(s) > 80:
        return False  # long text is likely data
    # Reject date-like strings (e.g. 2023-03-11, 16-11-2023, 25-1-2024, or with time 00:00:00)
    if re.search(r"\d{4}-\d{2}-\d{2}", s) or re.search(r"\d{1,2}-\d{1,2}-\d{2,4}", s):
        return False
    if "00:00:00" in s or re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", s):
        return False
    # Reject if whole string is a number
    try:
        float(s.replace(",", "").replace(" ", ""))
        return False  # numeric string is likely data
    except (ValueError, TypeError):
        pass
    return True


def row_looks_like_header(row: tuple, min_cells: int = 2) -> bool:
    """True if the row has enough header-like cells to be a header row (start of a table)."""
    non_empty = [c for c in row if c is not None and str(c).strip()]
    if len(non_empty) < min_cells:
        return False
    # First non-empty cell must look like a column title (e.g. "Date", not "15-11-2023")
    if not non_empty or not cell_looks_like_header_label(non_empty[0]):
        return False
    header_like_count = sum(1 for c in non_empty if cell_looks_like_header_label(c))
    return header_like_count >= min_cells


def row_is_mostly_empty(row: tuple, max_non_empty: int = 1) -> bool:
    """True if the row has at most max_non_empty non-empty cells (gap between tables)."""
    non_empty = [c for c in row if c is not None and str(c).strip()]
    return len(non_empty) <= max_non_empty


def detect_all_header_rows(sheet) -> List[int]:
    """
    Find all row indices that look like header rows (start of a new table).
    A row is treated as a header only if:
    - it looks like a header (2+ header-like cells), AND
    - it is row 1, OR the row immediately above is mostly empty (gap between tables).
    """
    header_indices: List[int] = []
    max_row = getattr(sheet, "max_row", 1000) or 1000
    prev_row: Optional[tuple] = None
    for row_idx, row in enumerate(
        sheet.iter_rows(max_row=max_row, values_only=True),
        start=1,
    ):
        row_tuple = tuple(row) if not isinstance(row, tuple) else row
        if not row_looks_like_header(row_tuple, min_cells=2):
            prev_row = row_tuple
            continue
        # Accept if first row, or after a gap, or previous row's first cell looked like data (new table without blank row)
        after_gap = prev_row is not None and row_is_mostly_empty(prev_row)
        prev_first = next((c for c in prev_row if c is not None and str(c).strip()), None) if prev_row else None
        prev_starts_with_data = prev_first is not None and not cell_looks_like_header_label(prev_first)
        if row_idx == 1 or after_gap or prev_starts_with_data:
            header_indices.append(row_idx)
        prev_row = row_tuple
    return header_indices
