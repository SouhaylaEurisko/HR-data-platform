"""
Service layer for XLSX import: workbook loading, field mapping,
table detection, row parsing, and sheet processing.
"""

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..models.candidate import Candidate, CandidateCreate
from .data_source_service import get_or_create_data_source


# ──────────────────────────────────────────────
# Field Mapping Configuration
# ──────────────────────────────────────────────

class FieldMappingConfig:
    """
    Configuration for mapping Excel column headers to Candidate fields.
    Supports common fields and sheet-specific overrides.
    """

    COMMON_FIELDS: Dict[str, List[str]] = {
        "full_name": [
            "candidate name", "full name", "applicant name",
            "fullname", "name", "candidate",
        ],
        "email": ["email", "e-mail", "email address", "e mail"],
        "nationality": [
            "nationality", "country of origin",
            "country of residence", "country",
        ],
        "date_of_birth": [
            "date of birth", "birth date", "dob",
            "birthday", "date of birth (dd/mm/yyyy)",
        ],
        "position": [
            "position", "job title", "role",
            "position applying for", "applied position", "job",
        ],
        "expected_salary": [
            "expected salary", "salary expectations",
            "salary expectation", "desired salary",
            "salary", "expected salary (usd)",
        ],
        "years_experience": [
            "years of experience", "total experience (years)",
            "total years of experience",
            "in total, how many years of experience do you have?",
            "experience", "yrs of experience", "YOE", "total experience",
        ],
        "current_address": [
            "current address", "current location",
            "current residence", "location", "address", "city",
        ],
        "notice_period": [
            "notice period", "notice period (days)",
            "notice period (weeks)", "notice period (months)",
            "availability", "when can you start?",
        ],
    }

    SHEET_OVERRIDES: Dict[str, Dict[str, List[str]]] = {}

    @classmethod
    def get_field_mappings(cls, sheet_name: Optional[str] = None) -> Dict[str, List[str]]:
        mappings = cls.COMMON_FIELDS.copy()
        if sheet_name and sheet_name in cls.SHEET_OVERRIDES:
            for field, headers in cls.SHEET_OVERRIDES[sheet_name].items():
                if field in mappings:
                    mappings[field] = headers + [h for h in mappings[field] if h not in headers]
                else:
                    mappings[field] = headers
        return mappings


# ──────────────────────────────────────────────
# Value conversion helpers
# ──────────────────────────────────────────────

def _to_json_safe(value: Any) -> Any:
    """Convert cell values to JSON-serializable primitives."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _truncate_string(value: Optional[str], max_length: int = 255) -> Optional[str]:
    """Truncate a string to the specified maximum length."""
    if value is None:
        return None
    if isinstance(value, str):
        return value[:max_length] if len(value) > max_length else value
    return str(value)[:max_length] if len(str(value)) > max_length else str(value)


def _to_float_or_none(value: Any) -> float | None:
    """Try to convert a cell value to float, handling ranges like '1800-2000'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    # Handle numeric ranges like "1800-2000"
    range_match = re.match(r"^\s*([\d\.,]+)\s*[-–]\s*([\d\.,]+)\s*$", text)
    if range_match:
        first, second = range_match.groups()

        def _to_single_float(part: str) -> float:
            cleaned_part = re.sub(r"[^0-9\.,]", "", part)
            if not cleaned_part:
                raise ValueError("Empty numeric part in range")
            cleaned_part = cleaned_part.replace(",", ".")
            return float(cleaned_part)

        try:
            lower = _to_single_float(first)
            upper = _to_single_float(second)
            return min(lower, upper)
        except ValueError:
            pass

    # Generic numeric parsing
    cleaned = re.sub(r"[^0-9\.,]", "", text)
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_date_or_none(value: Any):
    """Convert an XLSX cell value to a Python date."""
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


# ──────────────────────────────────────────────
# Row / header detection helpers
# ──────────────────────────────────────────────

def _is_empty_row(row: tuple) -> bool:
    return all(cell is None or (isinstance(cell, str) and not cell.strip()) for cell in row)


def _is_header_row(row: tuple) -> bool:
    """
    Determine if a row looks like a header row using known header patterns.
    
    This function is strict: it only matches rows that contain actual field names,
    not data values. It checks for multiple distinct header patterns and excludes
    rows that look like data (dates, names, job titles, etc.).
    """
    header_patterns: List[str] = []
    for patterns in FieldMappingConfig.COMMON_FIELDS.values():
        header_patterns.extend(p.lower() for p in patterns)

    # Require at least a few non-empty cells so we don't treat sparse rows as headers
    non_empty = [cell for cell in row if cell is not None and str(cell).strip()]
    if len(non_empty) < 3:
        return False

    header_like_count = 0
    seen_patterns: set[str] = set()
    data_like_indicators = 0

    for cell in non_empty:
        if not isinstance(cell, str):
            # Non-string cells (dates, numbers) are likely data, not headers
            data_like_indicators += 1
            continue
        
        text = cell.strip().lower()
        if not text:
            continue
        
        # Check if cell looks like data (not a header)
        # Dates in various formats
        if any(char.isdigit() for char in text) and (
            "/" in text or "-" in text or 
            re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', text) or
            re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
        ):
            data_like_indicators += 1
            continue
        
        # Pure numbers or numeric ranges
        if re.match(r'^\d+([-–]\d+)?$', text.replace(",", "").replace(".", "")):
            data_like_indicators += 1
            continue
        
        # Common data value patterns (not headers)
        data_patterns = [
            r'^\d+\+$',  # "3+", "5+"
            r'^\d+%',  # "96%", "34%"
            r'^\$\d+',  # "$4000", "$5000"
            r'^\d+\$',  # "4000$", "5000$"
            r'^yes$|^no$|^n/a$|^none$',  # Common yes/no values
            r'^immediately$|^freelance$|^employed$|^unemployed$',  # Employment status values
            r'^lebanese$|^egyptian$|^jordanian$|^syrian$|^saudi$',  # Nationality values (common ones)
        ]
        if any(re.match(pattern, text) for pattern in data_patterns):
            data_like_indicators += 1
            continue
        
        # Check if cell matches a header pattern
        # Use word boundaries or exact phrase matching to avoid false positives
        for pattern in header_patterns:
            # Match whole words or phrases, not substrings within data
            if pattern == text or f" {pattern} " in f" {text} " or text.startswith(pattern + " ") or text.endswith(" " + pattern):
                if pattern not in seen_patterns:
                    seen_patterns.add(pattern)
                    header_like_count += 1
                break

    # Require at least 3 distinct header patterns AND fewer data-like indicators
    # This ensures we're matching actual field name rows, not data rows
    return header_like_count >= 3 and data_like_indicators < header_like_count


def _find_contiguous_header_blocks(row: tuple) -> List[dict]:
    """
    Find contiguous blocks of header cells in a row.
    This helps identify side-by-side tables by detecting separate column ranges.
    
    A block is defined as a sequence of columns where:
    - At least 2 cells have content (to avoid single-cell noise)
    - Gaps of 1-2 empty cells are allowed within a block
    - Gaps of 3+ empty cells indicate a new block
    
    Returns a list of blocks, each with min_col, max_col, and headers.
    """
    blocks: List[dict] = []
    current_block_start = None
    current_block_headers = []
    empty_count = 0
    
    for col_i, cell in enumerate(row):
        has_content = cell is not None and str(cell).strip()
        
        if has_content:
            if current_block_start is None:
                # Start a new block
                current_block_start = col_i
                current_block_headers = [str(cell).strip()]
                empty_count = 0
            else:
                # Continue current block
                # Add any empty cells we accumulated (up to 2)
                while empty_count > 0 and empty_count <= 2:
                    current_block_headers.append("")
                    empty_count -= 1
                current_block_headers.append(str(cell).strip())
                empty_count = 0
        else:
            # Empty cell
            if current_block_start is not None:
                empty_count += 1
                # If we have 3+ consecutive empty cells, close the block
                if empty_count >= 3:
                    # Close the current block (excluding the empty cells)
                    blocks.append({
                        "min_col": current_block_start,
                        "max_col": col_i - empty_count,
                        "headers": current_block_headers,
                    })
                    current_block_start = None
                    current_block_headers = []
                    empty_count = 0
    
    # Close last block if any
    if current_block_start is not None:
        # Find the actual last column with content
        last_col = current_block_start + len(current_block_headers) - 1
        # Trim trailing empty headers
        while last_col >= current_block_start and not current_block_headers[last_col - current_block_start]:
            last_col -= 1
        
        if last_col >= current_block_start:
            blocks.append({
                "min_col": current_block_start,
                "max_col": last_col,
                "headers": current_block_headers[:last_col - current_block_start + 1],
            })
    
    # Filter out blocks that are too small (likely noise)
    return [b for b in blocks if len([h for h in b["headers"] if h]) >= 2]


def _detect_tables_in_sheet(sheet) -> List[dict]:
    """
    Detect multiple tables within a single sheet.
    
    Handles both:
    - Vertically stacked tables (one after another)
    - Side-by-side tables (adjacent column ranges)
    
    Each table is defined by its header row, data rows, and the COLUMN RANGE
    that belongs to it.
    """
    tables: List[dict] = []
    current_table_start = None
    current_headers = None
    current_min_col = None
    current_max_col = None
    # Track tables that need their end_row set (side-by-side tables)
    open_tables: List[int] = []  # Indices in tables list

    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if _is_header_row(row):
            # Close previous table if any
            if current_table_start is not None:
                tables.append({
                    "start_row": current_table_start,
                    "end_row": row_idx - 1,
                    "headers": current_headers,
                    "min_col": current_min_col,
                    "max_col": current_max_col,
                })
            
            # Close any open side-by-side tables (set their end_row)
            for table_idx in open_tables:
                if tables[table_idx]["end_row"] is None:
                    tables[table_idx]["end_row"] = row_idx - 1
            open_tables = []

            # Detect contiguous header blocks (for side-by-side tables)
            header_blocks = _find_contiguous_header_blocks(row)
            
            if not header_blocks:
                # Fallback: use entire row if no blocks detected
                first_col = None
                last_col = None
                for col_i, cell in enumerate(row):
                    if cell is not None and str(cell).strip():
                        if first_col is None:
                            first_col = col_i
                        last_col = col_i
                
                if first_col is not None:
                    header_blocks = [{
                        "min_col": first_col,
                        "max_col": last_col,
                        "headers": [str(row[col_i]).strip() if col_i < len(row) and row[col_i] is not None else ""
                                    for col_i in range(first_col, last_col + 1)],
                    }]
            
            # Process each header block as a separate table
            # If there are multiple blocks (side-by-side tables), create a table for each
            if header_blocks:
                # If we have a current table, close it first
                if current_table_start is not None:
                    tables.append({
                        "start_row": current_table_start,
                        "end_row": row_idx - 1,
                        "headers": current_headers,
                        "min_col": current_min_col,
                        "max_col": current_max_col,
                    })
                
                # For each block, create a separate table entry
                # Each block will be processed independently
                if len(header_blocks) == 1:
                    # Single table - track it for continuation
                    block = header_blocks[0]
                    current_table_start = row_idx
                    current_min_col = block["min_col"]
                    current_max_col = block["max_col"]
                    current_headers = block["headers"]
                else:
                    # Multiple side-by-side tables - create a table entry for each
                    # Each will be processed independently with its own column range
                    for block_idx, block in enumerate(header_blocks):
                        table_idx = len(tables)
                        tables.append({
                            "start_row": row_idx,
                            "end_row": None,  # Will be determined when next header is found
                            "headers": block["headers"],
                            "min_col": block["min_col"],
                            "max_col": block["max_col"],
                        })
                        open_tables.append(table_idx)
                    
                    # Don't track any of these as "current" since they're all separate
                    # Reset state so we can detect the next header row
                    current_table_start = None
                    current_headers = None
                    current_min_col = None
                    current_max_col = None

        elif current_table_start is not None:
            # Continue current table - empty rows are allowed within a table
            # Only header rows will close the current table
            pass

    # Close last table
    if current_table_start is not None:
        tables.append({
            "start_row": current_table_start,
            "end_row": None,
            "headers": current_headers,
            "min_col": current_min_col,
            "max_col": current_max_col,
        })
    
    # Close any remaining open side-by-side tables (set end_row to last row processed).
    # Note: We don't know the exact last row, so we keep end_row as None and let
    # _process_table handle it (it will process until the end of the sheet).
    # This loop is left for clarity in case we later want to add explicit bounds.
    for table_idx in open_tables:
        if tables[table_idx]["end_row"] is None:
            continue

    # Deduplicate tables: in some layouts our detection can register the same
    # header block twice. That leads to duplicated imports. We collapse tables
    # that have identical (start_row, end_row, min_col, max_col, headers).
    deduped: list[dict] = []
    seen_keys: set[tuple] = set()
    for t in tables:
        key = (
            t.get("start_row"),
            t.get("end_row"),
            t.get("min_col"),
            t.get("max_col"),
            tuple(t.get("headers") or []),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(t)

    return deduped


# ──────────────────────────────────────────────
# Field value matching
# ──────────────────────────────────────────────

def _find_field_value(normalized_headers: Dict[str, Any], possible_headers: List[str]) -> Optional[str]:
    """Find a field value by matching against possible header names."""
    for possible in possible_headers:
        possible_lower = possible.lower()
        if possible_lower in normalized_headers:
            value = normalized_headers[possible_lower]
            if value not in (None, ""):
                return str(value).strip()

    for possible in possible_headers:
        possible_lower = possible.lower()
        for header, value in normalized_headers.items():
            if value in (None, ""):
                continue
            if possible_lower in header:
                return str(value).strip()

    return None


# ──────────────────────────────────────────────
# Row → CandidateCreate mapping
# ──────────────────────────────────────────────

def _map_row_to_candidate_create(
    row_data: dict,
    data_source_id: int,
    row_index: int,
    source_sheet: str,  # Still needed for field mapping config
    mapping_config: Optional[FieldMappingConfig] = None,
) -> CandidateCreate:
    if mapping_config is None:
        mapping_config = FieldMappingConfig()

    normalized_headers = {
        k.strip().lower(): _to_json_safe(v)
        for k, v in row_data.items()
        if k is not None
    }

    field_mappings = mapping_config.get_field_mappings(source_sheet)

    mapped_data: Dict[str, Any] = {}
    for field_name, possible in field_mappings.items():
        value = _find_field_value(normalized_headers, possible)
        if value:
            mapped_data[field_name] = value

    raw_data = row_data.copy()
    date_of_birth = _to_date_or_none(mapped_data.get("date_of_birth"))

    raw_email = mapped_data.get("email")
    email_value: Optional[str] = None
    if raw_email:
        email_str = str(raw_email).strip()
        if "@" in email_str and "." in email_str:
            email_value = email_str

    raw_expected_salary = mapped_data.get("expected_salary")
    expected_salary = _to_float_or_none(raw_expected_salary)
    expected_salary_text = raw_expected_salary if raw_expected_salary is not None else None
    # Truncate expected_salary_text to 255 characters
    if expected_salary_text:
        expected_salary_text = _truncate_string(str(expected_salary_text), 255)

    years_experience = _to_float_or_none(mapped_data.get("years_experience"))

    return CandidateCreate(
        data_source_id=data_source_id,
        row_index=row_index,
        full_name=_truncate_string(mapped_data.get("full_name"), 255),
        email=_truncate_string(email_value, 255),
        nationality=_truncate_string(mapped_data.get("nationality"), 255),
        date_of_birth=date_of_birth,
        position=_truncate_string(mapped_data.get("position"), 255),
        expected_salary=expected_salary,
        expected_salary_text=expected_salary_text,
        current_address=_truncate_string(mapped_data.get("current_address"), 255),
        years_experience=years_experience,
        notice_period=_truncate_string(mapped_data.get("notice_period"), 255),
        raw_data=raw_data,
    )


# ──────────────────────────────────────────────
# Table & sheet processing
# ──────────────────────────────────────────────

def _process_table(
    sheet,
    table_info: dict,
    source_file: str,
    source_sheet: str,
    source_table_index: int,
    db: Session,
) -> dict:
    start_row = table_info["start_row"]
    end_row = table_info["end_row"]
    headers = table_info["headers"]
    min_col = table_info.get("min_col", 0)          # 0-based column index
    max_col = table_info.get("max_col", None)        # 0-based column index

    # Get or create DataSource for this file/sheet/table combination
    data_source = get_or_create_data_source(
        db=db,
        source_file=source_file,
        source_sheet=source_sheet,
        source_table_index=source_table_index,
    )

    created_count = 0
    skipped_empty = 0
    skipped_duplicates = 0
    row_errors: list[dict] = []

    # Read rows — always read all columns, then slice to the table's range
    if end_row is None:
        rows_to_process = sheet.iter_rows(min_row=start_row + 1, values_only=True)
    else:
        rows_to_process = sheet.iter_rows(min_row=start_row + 1, max_row=end_row, values_only=True)

    for row_idx, full_row in enumerate(rows_to_process, start=start_row + 1):
        # Slice the row to only the columns that belong to THIS table
        # Ensure we don't go beyond the actual row length
        if max_col is not None:
            # Make sure we don't exceed the row length
            actual_max_col = min(max_col + 1, len(full_row))
            row = full_row[min_col:actual_max_col]
        else:
            row = full_row[min_col:]

        # Ensure we have at least as many row values as headers (pad with None if needed)
        row_dict: Dict[str, Any] = {}
        num_cols = min(len(headers), len(row))

        # Map each header to its corresponding value
        for i in range(num_cols):
            header = headers[i] if i < len(headers) else None
            value = row[i] if i < len(row) else None
            
            if header and header.strip():
                header_key = header
                counter = 1
                while header_key in row_dict:
                    header_key = f"{header}_{counter}"
                    counter += 1
                row_dict[header_key] = _to_json_safe(value)
        
        # Also include any extra row values beyond headers (for raw_data completeness)
        for i in range(num_cols, len(row)):
            if row[i] is not None and str(row[i]).strip():
                # Use a generic column name
                row_dict[f"column_{i + 1}"] = _to_json_safe(row[i])

        if not any(value not in (None, "") for value in row_dict.values()):
            skipped_empty += 1
            continue

        try:
            candidate_create = _map_row_to_candidate_create(
                row_data=row_dict,
                data_source_id=data_source.id,
                row_index=row_idx,
                source_sheet=source_sheet,  # Still needed for field mapping
                mapping_config=FieldMappingConfig(),
            )

            if candidate_create.email:
                existing = db.query(Candidate).filter(
                    Candidate.email == candidate_create.email
                ).first()
                if existing:
                    skipped_duplicates += 1
                    continue

            candidate = Candidate(**candidate_create.model_dump())
            db.add(candidate)
            created_count += 1
        except Exception as exc:
            row_errors.append({"row_index": row_idx, "error": str(exc)})

    return {
        "created": created_count,
        "skipped_empty_rows": skipped_empty,
        "skipped_duplicates": skipped_duplicates,
        "row_errors": row_errors,
    }


def process_sheet(
    sheet,
    source_file: str,
    source_sheet: str,
    db: Session,
) -> dict:
    """Process a single sheet, detecting and handling multiple tables."""
    tables = _detect_tables_in_sheet(sheet)

    if not tables:
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            headers = next(rows_iter)
            header_list = [str(h).strip() if h is not None else "" for h in headers]
            tables = [{
                "start_row": 1,
                "end_row": None,
                "headers": header_list,
                "min_col": 0,
                "max_col": len(header_list) - 1,
            }]
        except StopIteration:
            return {
                "sheet_name": source_sheet,
                "tables_found": 0,
                "created": 0,
                "skipped_empty_rows": 0,
                "skipped_duplicates": 0,
                "row_errors": [],
                "table_results": [],
            }

    sheet_created = 0
    sheet_skipped_empty = 0
    sheet_skipped_duplicates = 0
    sheet_row_errors: list[dict] = []
    table_results: list[dict] = []

    for table_idx, table_info in enumerate(tables):
        table_result = _process_table(
            sheet=sheet,
            table_info=table_info,
            source_file=source_file,
            source_sheet=source_sheet,
            source_table_index=table_idx,
            db=db,
        )
        sheet_created += table_result["created"]
        sheet_skipped_empty += table_result["skipped_empty_rows"]
        sheet_skipped_duplicates += table_result["skipped_duplicates"]
        sheet_row_errors.extend(table_result["row_errors"])
        table_results.append({
            "table_index": table_idx,
            "start_row": table_info["start_row"],
            "end_row": table_info["end_row"],
            **table_result,
        })

    return {
        "sheet_name": source_sheet,
        "tables_found": len(tables),
        "created": sheet_created,
        "skipped_empty_rows": sheet_skipped_empty,
        "skipped_duplicates": sheet_skipped_duplicates,
        "row_errors": sheet_row_errors,
        "table_results": table_results,
    }


# ──────────────────────────────────────────────
# Workbook-level helpers
# ──────────────────────────────────────────────

async def load_workbook_from_file(file: UploadFile):
    """Validate and load an openpyxl workbook from an uploaded file."""
    if not file.filename.lower().endswith(".xlsx"):
        raise ValueError("Only .xlsx files are supported for this endpoint.")

    try:
        contents = await file.read()
        workbook = load_workbook(filename=BytesIO(contents), data_only=True)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to read XLSX file: {exc}") from exc

    if not workbook.sheetnames:
        raise ValueError("The provided XLSX file has no sheets.")

    return workbook


def determine_sheets_to_process(
    workbook, sheet_names: Optional[List[str]], import_all_sheets: bool
) -> List[str]:
    """Determine which sheets to process based on parameters."""
    all_sheet_names = workbook.sheetnames

    if import_all_sheets:
        return all_sheet_names

    if sheet_names:
        valid_sheets = [s for s in sheet_names if s in all_sheet_names]
        if not valid_sheets:
            raise ValueError(
                f"None of the requested sheets found. Available sheets: {', '.join(all_sheet_names)}"
            )
        return valid_sheets

    return all_sheet_names


def preview_workbook(workbook, filename: str) -> dict:
    """Return sheet metadata for preview without importing."""
    sheets_info = []
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        non_empty_rows = sum(
            1 for row in sheet.iter_rows(min_row=2, values_only=True)
            if any(cell is not None and str(cell).strip() for cell in row)
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


def import_workbook(
    workbook,
    filename: str,
    sheet_names: Optional[List[str]],
    import_all_sheets: bool,
    db: Session,
) -> dict:
    """
    Full import pipeline: determine sheets, process each one, commit, and
    return a summary dict ready to be returned as the API response.
    """
    sheets_to_process = determine_sheets_to_process(workbook, sheet_names, import_all_sheets)

    sheet_results: List[dict] = []
    total_created = 0
    total_skipped_empty = 0
    total_skipped_duplicates = 0
    all_row_errors: List[dict] = []

    for sheet_name in sheets_to_process:
        sheet = workbook[sheet_name]
        sheet_result = process_sheet(
            sheet=sheet,
            source_file=filename,
            source_sheet=sheet_name,
            db=db,
        )
        sheet_results.append(sheet_result)
        total_created += sheet_result["created"]
        total_skipped_empty += sheet_result["skipped_empty_rows"]
        total_skipped_duplicates += sheet_result["skipped_duplicates"]
        all_row_errors.extend(
            {**error, "sheet": sheet_name} for error in sheet_result["row_errors"]
        )

    db.commit()

    response: dict = {
        "file_name": filename,
        "sheets_processed": sheets_to_process,
        "total_created": total_created,
        "total_skipped_empty_rows": total_skipped_empty,
        "total_skipped_duplicates": total_skipped_duplicates,
        "sheet_results": sheet_results,
    }

    if all_row_errors:
        response["row_errors"] = all_row_errors

    return response
