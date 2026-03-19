"""
Import service — smart XLSX import pipeline with LLM column normalization,
programmatic validation, lookup resolution, and single-INSERT writes.
"""

import os
import re
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..models.candidate import Candidate
from ..models.enums import RelocationOpenness
from ..models.import_session import ImportSession
from .column_normalizer import (
    COLUMN_LABELS,
    ColumnMapping,
    NormalizationResult,
    get_available_columns,
    normalize_columns,
)
from .lookup_service import resolve_lookup_value
from .type_detector import create_custom_field


# ──────────────────────────────────────────────
# Temp file storage for two-phase import
# ──────────────────────────────────────────────

_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "hr_import_uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


def _save_temp_file(session_id: int, contents: bytes) -> str:
    path = os.path.join(_UPLOAD_DIR, f"session_{session_id}.xlsx")
    with open(path, "wb") as f:
        f.write(contents)
    return path


def _load_temp_file(session_id: int):
    path = os.path.join(_UPLOAD_DIR, f"session_{session_id}.xlsx")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Temp file for session {session_id} not found.")
    return load_workbook(filename=path, data_only=True)


def _cleanup_temp_file(session_id: int):
    path = os.path.join(_UPLOAD_DIR, f"session_{session_id}.xlsx")
    if os.path.exists(path):
        os.remove(path)


# ──────────────────────────────────────────────
# Value conversion helpers
# ──────────────────────────────────────────────

def _to_json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _normalize_numeric_string_to_decimal_str(cleaned: str) -> Optional[str]:
    """
    Turn a cleaned string (digits, optional . and , and leading -) into a form
    Decimal() accepts.
    """
    s = cleaned.strip()
    if not s:
        return None
    neg = False
    if s.startswith("-"):
        neg = True
        s = s[1:]
    if not s or not re.fullmatch(r"[\d\.,]+", s):
        return None

    def with_sign(num: str) -> str:
        return ("-" if neg else "") + num

    if "," in s and "." in s:
        # Last separator is the decimal separator
        if s.rfind(",") > s.rfind("."):
            # e.g. 1.234,56
            num = s.replace(".", "").replace(",", ".")
        else:
            # e.g. 1,234.56
            num = s.replace(",", "")
        return with_sign(num)

    if "," in s:
        parts = s.split(",")
        # Multiple groups, last segment short → decimal comma (1234,5 / 1234,56)
        if len(parts) > 1 and len(parts[-1]) <= 2:
            num = "".join(parts[:-1]) + "." + parts[-1]
        else:
            # Thousands only: 5,000
            num = "".join(parts)
        return with_sign(num)

    if "." in s:
        parts = s.split(".")
        # Dot as thousands: every segment after the first is exactly 3 digits
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]):
            return with_sign("".join(parts))
        return with_sign(s)

    return with_sign(s)


def _to_decimal_or_none(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9\.,\-]", "", text)
    if not cleaned:
        return None
    # Handle ranges: take the lower bound
    range_match = re.match(r"^([\d\.,]+)\s*[-–]\s*([\d\.,]+)$", cleaned)
    if range_match:
        cleaned = range_match.group(1)
    normalized = _normalize_numeric_string_to_decimal_str(cleaned)
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _to_date_or_none(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _to_bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "1", "y", "oui", "employed"):
        return True
    if text in ("false", "no", "0", "n", "non", "unemployed", "not employed"):
        return False
    return None


def _to_relocation_openness_or_none(value: Any) -> Optional[RelocationOpenness]:
    """Map Excel/form values to RelocationOpenness (yes | no | for_missions_only)."""
    if value is None:
        return None
    if isinstance(value, RelocationOpenness):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    # Third option (Google Forms / HR wording)
    if "mission" in text:
        return RelocationOpenness.for_missions_only
    if text in ("true", "yes", "1", "y", "oui"):
        return RelocationOpenness.yes
    if text in ("false", "no", "0", "n", "non"):
        return RelocationOpenness.no
    # Try enum value / name
    for member in RelocationOpenness:
        if text == member.value or text == member.name.lower():
            return member
    return None


def _to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    # Handle textual notice periods like "2 months" -> 60
    months_match = re.match(r"(\d+)\s*months?", text, re.IGNORECASE)
    if months_match:
        return int(months_match.group(1)) * 30
    weeks_match = re.match(r"(\d+)\s*weeks?", text, re.IGNORECASE)
    if weeks_match:
        return int(weeks_match.group(1)) * 7
    days_match = re.match(r"(\d+)\s*days?", text, re.IGNORECASE)
    if days_match:
        return int(days_match.group(1))
    cleaned = re.sub(r"[^0-9]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def _truncate(value: Optional[str], max_len: int = 255) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s[:max_len] if len(s) > max_len else s


# ──────────────────────────────────────────────
# Header / table detection (kept from original)
# ──────────────────────────────────────────────

def _is_empty_row(row: tuple) -> bool:
    return all(c is None or (isinstance(c, str) and not c.strip()) for c in row)


def _cell_looks_like_header_label(cell: Any) -> bool:
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


def _row_looks_like_header(row: tuple, min_cells: int = 2) -> bool:
    """True if the row has enough header-like cells to be a header row (start of a table)."""
    non_empty = [c for c in row if c is not None and str(c).strip()]
    if len(non_empty) < min_cells:
        return False
    # First non-empty cell must look like a column title (e.g. "Date", not "15-11-2023")
    if not non_empty or not _cell_looks_like_header_label(non_empty[0]):
        return False
    header_like_count = sum(1 for c in non_empty if _cell_looks_like_header_label(c))
    return header_like_count >= min_cells


def _row_is_mostly_empty(row: tuple, max_non_empty: int = 1) -> bool:
    """True if the row has at most max_non_empty non-empty cells (gap between tables)."""
    non_empty = [c for c in row if c is not None and str(c).strip()]
    return len(non_empty) <= max_non_empty


def _detect_header_row(sheet) -> Optional[int]:
    """Find the first row that looks like a header (3+ string cells)."""
    for row_idx, row in enumerate(sheet.iter_rows(max_row=20, values_only=True), start=1):
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) >= 3:
            str_count = sum(1 for c in non_empty if isinstance(c, str))
            if str_count >= 3:
                return row_idx
    return 1


def _detect_all_header_rows(sheet) -> List[int]:
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
        if not _row_looks_like_header(row_tuple, min_cells=2):
            prev_row = row_tuple
            continue
        # Accept if first row, or after a gap, or previous row's first cell looked like data (new table without blank row)
        after_gap = prev_row is not None and _row_is_mostly_empty(prev_row)
        prev_first = next((c for c in prev_row if c is not None and str(c).strip()), None) if prev_row else None
        prev_starts_with_data = prev_first is not None and not _cell_looks_like_header_label(prev_first)
        if row_idx == 1 or after_gap or prev_starts_with_data:
            header_indices.append(row_idx)
        prev_row = row_tuple
    return header_indices


# ──────────────────────────────────────────────
# Lookup columns requiring ID resolution
# ──────────────────────────────────────────────

LOOKUP_COLUMN_MAP = {
    "residency_type_id": "residency_type",
    "marital_status_id": "marital_status",
    "passport_validity_status_id": "passport_validity",
    "workplace_type_id": "workplace_type",
    "employment_type_id": "employment_type",
    "education_level_id": "education_level",
    "education_completion_status_id": "education_completion",
}

BOOLEAN_COLUMNS = {
    "has_transportation",
    "is_overtime_flexible", "is_contract_flexible",
    "is_employed",
}

DECIMAL_COLUMNS = {"current_salary", "expected_salary_remote", "expected_salary_onsite", "years_of_experience"}

INT_COLUMNS = {
    "number_of_dependents",
}

DATE_COLUMNS = {"date_of_birth"}

STRING_COLUMNS = {
    "full_name", "email",
    "nationality", "current_address", "religion_sect",
    "applied_position", "applied_position_location",
    "notice_period",
}


# ──────────────────────────────────────────────
# Core: map a row to candidate kwargs
# ──────────────────────────────────────────────

def _map_row(
    row_data: Dict[str, Any],
    column_mappings: Dict[str, str],
    org_id: int,
    db: Session,
) -> Dict[str, Any]:
    """
    Convert a raw Excel row dict to candidate INSERT kwargs using confirmed column mappings.
    column_mappings: {excel_header_lower: db_column}
    """
    candidate_kwargs: Dict[str, Any] = {}
    custom_fields: Dict[str, Any] = {}
    raw_import_data = {k: _to_json_safe(v) for k, v in row_data.items()}

    for excel_header, raw_value in row_data.items():
        header_lower = excel_header.strip().lower()
        db_col = column_mappings.get(header_lower)
        if not db_col:
            continue

        # Custom field handling
        if db_col.startswith("custom:"):
            cf_key = db_col[len("custom:"):]
            custom_fields[cf_key] = _to_json_safe(raw_value)
            continue

        # Lookup columns: resolve text to ID
        if db_col in LOOKUP_COLUMN_MAP:
            category_code = LOOKUP_COLUMN_MAP[db_col]
            resolved_id = resolve_lookup_value(db, category_code, org_id, str(raw_value) if raw_value else "")
            if resolved_id:
                candidate_kwargs[db_col] = resolved_id
            continue

        # Type-specific conversion
        if db_col == "is_open_for_relocation":
            val = _to_relocation_openness_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in BOOLEAN_COLUMNS:
            val = _to_bool_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in DECIMAL_COLUMNS:
            val = _to_decimal_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in INT_COLUMNS:
            val = _to_int_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col in DATE_COLUMNS:
            val = _to_date_or_none(raw_value)
            if val is not None:
                candidate_kwargs[db_col] = val
        elif db_col == "applied_at":
            if isinstance(raw_value, datetime):
                candidate_kwargs[db_col] = raw_value
            elif isinstance(raw_value, str):
                try:
                    candidate_kwargs[db_col] = datetime.fromisoformat(raw_value.strip())
                except ValueError:
                    pass
        elif db_col == "tech_stack":
            if isinstance(raw_value, str):
                candidate_kwargs[db_col] = [s.strip() for s in raw_value.split(",") if s.strip()]
            elif isinstance(raw_value, list):
                candidate_kwargs[db_col] = raw_value
        elif db_col == "email":
            email_str = str(raw_value).strip() if raw_value else ""
            if "@" in email_str and "." in email_str:
                candidate_kwargs[db_col] = _truncate(email_str, 320)
        elif db_col in STRING_COLUMNS:
            if raw_value is not None and str(raw_value).strip():
                candidate_kwargs[db_col] = _truncate(str(raw_value), 255)

    candidate_kwargs["custom_fields"] = custom_fields if custom_fields else {}
    candidate_kwargs["raw_import_data"] = raw_import_data
    return candidate_kwargs


# ──────────────────────────────────────────────
# Workbook helpers
# ──────────────────────────────────────────────

async def load_workbook_from_file(file: UploadFile):
    if not file.filename.lower().endswith(".xlsx"):
        raise ValueError("Only .xlsx files are supported.")
    try:
        contents = await file.read()
        workbook = load_workbook(filename=BytesIO(contents), data_only=True)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to read XLSX file: {exc}") from exc
    if not workbook.sheetnames:
        raise ValueError("The provided XLSX file has no sheets.")
    return workbook, contents


def preview_workbook(workbook, filename: str) -> dict:
    sheets_info = []
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        non_empty_rows = sum(
            1 for row in sheet.iter_rows(min_row=2, values_only=True)
            if any(c is not None and str(c).strip() for c in row)
        )
        sheets_info.append({
            "name": sheet_name,
            "max_row": sheet.max_row,
            "data_rows": non_empty_rows,
        })
    return {
        "file_name": filename,
        "sheets": sheets_info,
        "total_sheets": len(sheets_info),
    }


def _extract_headers_from_row(sheet, row_idx: int) -> List[str]:
    """Extract header strings from a specific row (strip and blank as empty)."""
    headers = []
    for row in sheet.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True):
        for cell in row:
            if cell is not None and str(cell).strip():
                headers.append(str(cell).strip())
            else:
                headers.append("")
    return headers


def _extract_headers_from_sheet(sheet) -> List[str]:
    """Extract header strings from the first detected header row (backward compat)."""
    header_row_idx = _detect_header_row(sheet)
    return _extract_headers_from_row(sheet, header_row_idx)


def _extract_all_headers_from_sheet(sheet) -> List[str]:
    """Collect unique headers from every table (every header row) in the sheet."""
    seen = set()
    ordered = []
    for row_idx in _detect_all_header_rows(sheet):
        for h in _extract_headers_from_row(sheet, row_idx):
            if h and h.lower() not in seen:
                seen.add(h.lower())
                ordered.append(h)
    return ordered


def _extract_all_headers(workbook, sheet_names: List[str]) -> List[str]:
    """Collect unique headers across all tables in all selected sheets."""
    seen = set()
    ordered = []
    for name in sheet_names:
        sheet = workbook[name]
        for h in _extract_all_headers_from_sheet(sheet):
            if h and h.lower() not in seen:
                seen.add(h.lower())
                ordered.append(h)
    return ordered


# ──────────────────────────────────────────────
# Phase A: Analyze
# ──────────────────────────────────────────────

async def analyze_workbook(
    workbook,
    contents: bytes,
    filename: str,
    sheet_names: List[str],
    org_id: int,
    user_id: int,
    db: Session,
) -> dict:
    """
    Phase A of the two-phase import.
    Parse headers, run column normalization, create ImportSession, save temp file.
    """
    session = ImportSession(
        organization_id=org_id,
        uploaded_by_user_id=user_id,
        original_filename=filename,
        status="pending",
    )
    db.add(session)
    db.flush()

    _save_temp_file(session.id, contents)

    all_headers = _extract_all_headers(workbook, sheet_names)
    norm_result = await normalize_columns(all_headers, db, org_id, use_llm=True)

    db.commit()

    def _serialize_mapping(m: ColumnMapping) -> dict:
        return {
            "excel_header": m.excel_header,
            "db_column": m.db_column,
            "db_column_label": COLUMN_LABELS.get(m.db_column, m.db_column) if m.db_column else None,
            "confidence": m.confidence,
            "source": m.source,
        }

    already_mapped = set()
    for m in norm_result.matched:
        if m.db_column:
            already_mapped.add(m.db_column)
    for m in norm_result.suggested:
        if m.db_column:
            already_mapped.add(m.db_column)

    available = get_available_columns(db, org_id)

    return {
        "session_id": session.id,
        "filename": filename,
        "sheets": sheet_names,
        "matched_columns": [_serialize_mapping(m) for m in norm_result.matched],
        "suggested_columns": [_serialize_mapping(m) for m in norm_result.suggested],
        "unmatched_columns": [_serialize_mapping(m) for m in norm_result.unmatched],
        "available_columns": available,
        "already_mapped": list(already_mapped),
    }


# ──────────────────────────────────────────────
# Phase B: Confirm and import
# ──────────────────────────────────────────────

def confirm_and_import(
    session_id: int,
    confirmed_mappings: Dict[str, str],
    new_custom_fields: List[Dict[str, Any]],
    skip_columns: List[str],
    sheet_names: List[str],
    org_id: int,
    db: Session,
) -> dict:
    """
    Phase B: receive confirmed mappings, create custom fields,
    validate rows, insert candidates, update import session.

    confirmed_mappings: {excel_header_lower: db_column}
    new_custom_fields: [{"header": "...", "label": "..."}, ...]
    skip_columns: [excel_header, ...]
    """
    session = db.query(ImportSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError(f"Import session {session_id} not found.")
    if session.status != "pending":
        raise ValueError(f"Session is already {session.status}.")

    session.status = "processing"
    db.flush()

    # Create any new custom fields
    workbook = _load_temp_file(session_id)
    for cf_spec in new_custom_fields:
        header = cf_spec["header"]
        label = cf_spec.get("label", header)
        # Collect sample values from sheets
        values = _collect_column_values(workbook, sheet_names, header)
        cfd, _ = create_custom_field(db, org_id, label, values)
        confirmed_mappings[header.strip().lower()] = f"custom:{cfd.field_key}"

    # Build final column mapping (lowercase header -> db_column)
    col_map = {}
    for header, db_col in confirmed_mappings.items():
        col_map[header.strip().lower()] = db_col

    # Process all sheets
    total_created = 0
    total_skipped_empty = 0
    total_skipped_duplicates = 0
    total_errors = 0
    sheet_results = []
    all_row_errors = []

    for sheet_name in sheet_names:
        sheet = workbook[sheet_name]
        result = _process_sheet(sheet, sheet_name, col_map, org_id, session.id, db)
        total_created += result["created"]
        total_skipped_empty += result["skipped_empty"]
        total_skipped_duplicates += result["skipped_duplicates"]
        total_errors += len(result["row_errors"])
        sheet_results.append(result)
        all_row_errors.extend(
            {**e, "sheet": sheet_name} for e in result["row_errors"]
        )

    # Update session
    session.total_rows = total_created + total_skipped_empty + total_skipped_duplicates + total_errors
    session.imported_rows = total_created
    session.skipped_rows = total_skipped_empty + total_skipped_duplicates
    session.error_rows = total_errors
    session.status = "completed" if total_errors == 0 else "completed"
    session.completed_at = datetime.utcnow()
    session.summary = {
        "sheets": sheet_results,
        "row_errors": all_row_errors[:100],
    }

    db.commit()
    _cleanup_temp_file(session_id)

    return {
        "session_id": session_id,
        "status": session.status,
        "total_created": total_created,
        "total_skipped_empty_rows": total_skipped_empty,
        "total_skipped_duplicates": total_skipped_duplicates,
        "total_errors": total_errors,
        "sheet_results": sheet_results,
        "row_errors": all_row_errors[:50],
    }


def _collect_column_values(workbook, sheet_names: List[str], header: str) -> List[Any]:
    """Collect sample values from a specific column across all tables in all sheets."""
    values = []
    header_lower = header.strip().lower()
    for name in sheet_names:
        sheet = workbook[name]
        header_row_indices = _detect_all_header_rows(sheet)
        max_row = getattr(sheet, "max_row", 0) or 0
        for t_idx, header_row_idx in enumerate(header_row_indices):
            next_header = (
                header_row_indices[t_idx + 1] - 1
                if t_idx + 1 < len(header_row_indices)
                else max_row
            )
            headers_row = list(sheet.iter_rows(
                min_row=header_row_idx, max_row=header_row_idx, values_only=True
            ))[0]
            col_idx = None
            for i, h in enumerate(headers_row):
                if h and str(h).strip().lower() == header_lower:
                    col_idx = i
                    break
            if col_idx is None:
                continue
            for row in sheet.iter_rows(
                min_row=header_row_idx + 1, max_row=next_header, values_only=True
            ):
                if col_idx < len(row) and row[col_idx] is not None:
                    values.append(row[col_idx])
                if len(values) >= 100:
                    return values
    return values


def _process_sheet(
    sheet,
    sheet_name: str,
    col_map: Dict[str, str],
    org_id: int,
    session_id: int,
    db: Session,
) -> dict:
    """
    Process a single sheet; supports multiple tables per sheet.
    Each table starts at a header row; we detect all header rows and process
    the data rows between consecutive headers (or from header to end of sheet).
    """
    header_row_indices = _detect_all_header_rows(sheet)
    if not header_row_indices:
        # Fallback: treat row 1 as header (empty sheet or no header-like row)
        header_row_indices = [1]

    created = 0
    skipped_empty = 0
    skipped_duplicates = 0  # retained for API shape; email duplicates are allowed (multiple applications)
    row_errors = []

    max_row = getattr(sheet, "max_row", 0) or 0

    for t_idx, header_row_idx in enumerate(header_row_indices):
        # Data rows: from row after this header until the next header (exclusive) or end of sheet
        next_header = (
            header_row_indices[t_idx + 1]
            if t_idx + 1 < len(header_row_indices)
            else max_row + 1
        )
        data_start = header_row_idx + 1
        data_end = next_header - 1

        if data_end < data_start:
            continue

        headers_row = list(sheet.iter_rows(
            min_row=header_row_idx, max_row=header_row_idx, values_only=True
        ))[0]
        headers = [str(h).strip() if h else "" for h in headers_row]

        for row_idx, row in enumerate(
            sheet.iter_rows(min_row=data_start, max_row=data_end, values_only=True),
            start=data_start,
        ):
            row_dict = {}
            for i, h in enumerate(headers):
                if h and i < len(row):
                    row_dict[h] = row[i]

            if not any(v is not None and str(v).strip() for v in row_dict.values()):
                skipped_empty += 1
                continue

            try:
                candidate_kwargs = _map_row(row_dict, col_map, org_id, db)
                candidate_kwargs["organization_id"] = org_id
                candidate_kwargs["import_session_id"] = session_id
                candidate_kwargs["import_sheet"] = sheet_name

                candidate = Candidate(**candidate_kwargs)
                db.add(candidate)
                created += 1
            except Exception as exc:
                row_errors.append({"row_index": row_idx, "error": str(exc)})

    return {
        "sheet_name": sheet_name,
        "created": created,
        "skipped_empty": skipped_empty,
        "skipped_duplicates": skipped_duplicates,
        "row_errors": row_errors,
    }
