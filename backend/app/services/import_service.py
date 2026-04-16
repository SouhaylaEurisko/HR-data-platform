"""
Import service — smart XLSX import pipeline with LLM column normalization,
programmatic validation, lookup resolution, and single-INSERT writes.
"""

import os
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Set, Protocol

from fastapi import UploadFile
from openpyxl import load_workbook

from ..exceptions import BusinessRuleError, NotFoundError
from ..factories.candidate_import_factory import map_import_row, split_profile_and_application
from ..repository.import_repository import ImportRepositoryProtocol
from .column_normalizer_service import (
    ColumnNormalizerServiceProtocol,
    ColumnMapping,
    COLUMN_LABELS,
)
from .import_header_detection_service import detect_all_header_rows
from .lookup_service import LookupServiceProtocol
from .custom_field_type_service import (
    CustomFieldTypeServiceProtocol,
)


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
# Workbook helpers
# ──────────────────────────────────────────────

async def load_workbook_from_file(file: UploadFile):
    if not file.filename.lower().endswith(".xlsx"):
        raise BusinessRuleError("Only .xlsx files are supported.")
    try:
        contents = await file.read()
        workbook = load_workbook(filename=BytesIO(contents), data_only=True)
    except ValueError as exc:
        raise BusinessRuleError(str(exc)) from exc
    except Exception as exc:
        raise BusinessRuleError(f"Failed to read XLSX file: {exc}") from exc
    if not workbook.sheetnames:
        raise BusinessRuleError("The provided XLSX file has no sheets.")
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


def _extract_all_headers_from_sheet(sheet) -> List[str]:
    """Collect unique headers from every table (every header row) in the sheet."""
    seen = set()
    ordered = []
    for row_idx in detect_all_header_rows(sheet):
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


def _collect_column_values(workbook, sheet_names: List[str], header: str) -> List[Any]:
    """Collect sample values from a specific column across all tables in all sheets."""
    values = []
    header_lower = header.strip().lower()
    for name in sheet_names:
        sheet = workbook[name]
        header_row_indices = detect_all_header_rows(sheet)
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


class ImportServiceProtocol(Protocol):
    async def load_workbook_from_file(self, file: UploadFile): ...
    def preview_workbook(self, workbook, filename: str) -> dict: ...
    async def analyze_workbook(
        self,
        workbook,
        contents: bytes,
        filename: str,
        sheet_names: List[str],
        org_id: int,
        user_id: int,
    ) -> dict: ...
    def check_import_name_conflicts(
        self,
        *,
        org_id: int,
        filename: str,
        sheet_names: List[str],
    ) -> dict: ...
    def confirm_and_import(
        self,
        session_id: int,
        confirmed_mappings: Dict[str, str],
        new_custom_fields: List[Dict[str, Any]],
        skip_columns: List[str],
        sheet_names: List[str],
        org_id: int,
    ) -> dict: ...


class ImportService:
    def __init__(
        self,
        import_repo: ImportRepositoryProtocol,
        lookup_service: LookupServiceProtocol,
        custom_field_type_service: CustomFieldTypeServiceProtocol,
        column_normalizer_service: ColumnNormalizerServiceProtocol,
    ) -> None:
        self._import_repo = import_repo
        self._lookup_service = lookup_service
        self._custom_field_type_service = custom_field_type_service
        self._column_normalizer_service = column_normalizer_service

    def _process_sheet(
        self,
        sheet,
        sheet_name: str,
        col_map: Dict[str, str],
        org_id: int,
        session_id: int,
        skip_headers_lower: Optional[Set[str]] = None,
    ) -> dict:
        skipped = skip_headers_lower or set()
        header_row_indices = detect_all_header_rows(sheet)
        if not header_row_indices:
            header_row_indices = [1]

        created = 0
        skipped_empty = 0
        skipped_duplicates = 0
        row_errors = []
        max_row = getattr(sheet, "max_row", 0) or 0

        for t_idx, header_row_idx in enumerate(header_row_indices):
            next_header = (
                header_row_indices[t_idx + 1]
                if t_idx + 1 < len(header_row_indices)
                else max_row + 1
            )
            data_start = header_row_idx + 1
            data_end = next_header - 1
            if data_end < data_start:
                continue

            headers_row = list(
                sheet.iter_rows(min_row=header_row_idx, max_row=header_row_idx, values_only=True)
            )[0]
            headers = [str(h).strip() if h else "" for h in headers_row]

            for row_idx, row in enumerate(
                sheet.iter_rows(min_row=data_start, max_row=data_end, values_only=True),
                start=data_start,
            ):
                row_dict = {}
                for i, h in enumerate(headers):
                    if h and i < len(row):
                        if str(h).strip().lower() in skipped:
                            continue
                        row_dict[h] = row[i]

                if not any(v is not None and str(v).strip() for v in row_dict.values()):
                    skipped_empty += 1
                    continue

                try:
                    mapped = map_import_row(self._lookup_service, row_dict, col_map, org_id)
                    mapped["organization_id"] = org_id
                    mapped["import_session_id"] = session_id
                    profile_kw, app_kw = split_profile_and_application(mapped)
                    self._import_repo.insert_imported_candidate_row(profile_kw, app_kw)
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

    async def load_workbook_from_file(self, file: UploadFile):
        return await load_workbook_from_file(file)

    def preview_workbook(self, workbook, filename: str) -> dict:
        return preview_workbook(workbook, filename)

    async def analyze_workbook(
        self,
        workbook,
        contents: bytes,
        filename: str,
        sheet_names: List[str],
        org_id: int,
        user_id: int,
    ) -> dict:
        session = self._import_repo.create_pending_import_session(
            org_id=org_id,
            user_id=user_id,
            original_filename=filename,
        )
        _save_temp_file(session.id, contents)

        all_headers = _extract_all_headers(workbook, sheet_names)
        norm_result = await self._column_normalizer_service.normalize_columns(
            all_headers,
            org_id,
            use_llm=True,
        )
        self._import_repo.commit_import_transaction()

        def _serialize_mapping(m: ColumnMapping) -> dict:
            return {
                "excel_header": m.excel_header,
                "db_column": m.db_column,
                "db_column_label": COLUMN_LABELS.get(m.db_column, m.db_column) if m.db_column else None,
                "confidence": m.confidence,
                "source": m.source,
            }

        already_mapped = {
            m.db_column
            for m in [*norm_result.matched, *norm_result.suggested]
            if m.db_column
        }
        available = self._column_normalizer_service.get_available_columns(org_id)
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

    def check_import_name_conflicts(
        self,
        *,
        org_id: int,
        filename: str,
        sheet_names: List[str],
    ) -> dict:
        normalized_filename = str(filename or "").strip()
        normalized_sheets = [str(s).strip() for s in (sheet_names or []) if str(s).strip()]
        filename_lower = normalized_filename.lower() if normalized_filename else ""
        filename_exists = self._import_repo.import_filename_exists(org_id, filename_lower)

        existing_sheets_map: dict[str, str] = {}
        if filename_lower:
            for sheet_val in self._import_repo.distinct_import_sheet_strings_for_filename(
                org_id, filename_lower
            ):
                for part in sheet_val.split(","):
                    p = part.strip()
                    if p:
                        existing_sheets_map[p.lower()] = p

        duplicate_sheets = []
        for sheet in normalized_sheets:
            match = existing_sheets_map.get(sheet.lower())
            if match:
                duplicate_sheets.append(match)
        duplicate_sheets = list(dict.fromkeys(duplicate_sheets))

        return {
            "filename_exists": filename_exists,
            "duplicate_sheets": duplicate_sheets,
            "has_duplicates": bool(duplicate_sheets),
        }

    def confirm_and_import(
        self,
        session_id: int,
        confirmed_mappings: Dict[str, str],
        new_custom_fields: List[Dict[str, Any]],
        skip_columns: List[str],
        sheet_names: List[str],
        org_id: int,
    ) -> dict:
        session = self._import_repo.get_import_session_by_id(session_id)
        if not session:
            raise NotFoundError(f"Import session {session_id} not found.")
        if session.status != "pending":
            raise BusinessRuleError(f"Session is already {session.status}.")

        self._import_repo.mark_import_session_processing(session)
        workbook = _load_temp_file(session_id)

        for cf_spec in new_custom_fields:
            header = cf_spec["header"]
            label = cf_spec.get("label", header)
            values = _collect_column_values(workbook, sheet_names, header)
            cfd, _ = self._custom_field_type_service.create_custom_field(org_id, label, values)
            confirmed_mappings[header.strip().lower()] = f"custom:{cfd.field_key}"

        col_map = {header.strip().lower(): db_col for header, db_col in confirmed_mappings.items()}
        skip_lower: Set[str] = {
            str(h).strip().lower()
            for h in (skip_columns or [])
            if h is not None and str(h).strip()
        }
        for hl in skip_lower:
            col_map.pop(hl, None)

        total_created = 0
        total_skipped_empty = 0
        total_skipped_duplicates = 0
        total_errors = 0
        sheet_results = []
        all_row_errors = []

        for sheet_name in sheet_names:
            sheet = workbook[sheet_name]
            result = self._process_sheet(sheet, sheet_name, col_map, org_id, session.id, skip_lower)
            total_created += result["created"]
            total_skipped_empty += result["skipped_empty"]
            total_skipped_duplicates += result["skipped_duplicates"]
            total_errors += len(result["row_errors"])
            sheet_results.append(result)
            all_row_errors.extend({**e, "sheet": sheet_name} for e in result["row_errors"])

        sheet_labels = [str(s).strip() for s in sheet_names if s is not None and str(s).strip()]
        import_sheet_val = ", ".join(dict.fromkeys(sheet_labels))[:255] if sheet_labels else None
        self._import_repo.complete_import_session_and_commit(
            session,
            import_sheet=import_sheet_val,
            total_rows=total_created + total_skipped_empty + total_skipped_duplicates + total_errors,
            imported_rows=total_created,
            skipped_rows=total_skipped_empty + total_skipped_duplicates,
            error_rows=total_errors,
            completed_at=datetime.utcnow(),
            summary={"sheets": sheet_results, "row_errors": all_row_errors[:100]},
        )
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
