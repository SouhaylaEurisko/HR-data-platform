"""
Router: XLSX upload, preview, analyze, confirm, and one-shot import endpoints.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_db
from ..services.import_service import (
    analyze_workbook,
    confirm_and_import,
    import_workbook_oneshot,
    load_workbook_from_file,
    preview_workbook,
)

router = APIRouter(prefix="/api/import", tags=["import"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class ConfirmImportRequest(BaseModel):
    session_id: int
    confirmed_mappings: Dict[str, str]
    new_custom_fields: List[Dict[str, Any]] = []
    skip_columns: List[str] = []
    sheet_names: List[str]
    org_id: int


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/xlsx/preview", summary="Preview XLSX file structure")
async def preview_xlsx(file: UploadFile = File(...)) -> dict:
    try:
        workbook, _ = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return preview_workbook(workbook, file.filename or "unknown.xlsx")


@router.post("/xlsx/analyze", summary="Analyze XLSX and suggest column mappings")
async def analyze_xlsx(
    file: UploadFile = File(...),
    sheet_names: Optional[List[str]] = Query(None),
    import_all_sheets: bool = Query(False),
    org_id: int = Query(1, description="Organization ID"),
    user_id: int = Query(1, description="Uploading user ID"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Phase A of two-phase import.
    Parses the file, runs column normalization (programmatic + LLM),
    and returns matched / suggested / unmatched columns for HR review.
    """
    try:
        workbook, contents = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sheets_to_process = _resolve_sheets(workbook, sheet_names, import_all_sheets)

    try:
        return await analyze_workbook(
            workbook, contents, file.filename or "unknown.xlsx",
            sheets_to_process, org_id, user_id, db,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/xlsx/confirm", summary="Confirm column mappings and import")
def confirm_xlsx(
    body: ConfirmImportRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Phase B of two-phase import.
    Receives confirmed column mappings from HR and imports the data.
    """
    try:
        return confirm_and_import(
            session_id=body.session_id,
            confirmed_mappings=body.confirmed_mappings,
            new_custom_fields=body.new_custom_fields,
            skip_columns=body.skip_columns,
            sheet_names=body.sheet_names,
            org_id=body.org_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/xlsx", summary="One-shot upload and import (backward compatible)")
async def import_xlsx(
    file: UploadFile = File(...),
    sheet_names: Optional[List[str]] = Query(None),
    import_all_sheets: bool = Query(False),
    org_id: int = Query(1, description="Organization ID"),
    user_id: int = Query(1, description="Uploading user ID"),
    db: Session = Depends(get_db),
) -> dict:
    """
    One-shot import: auto-accepts all high-confidence column mappings
    and creates custom fields for unmatched columns.
    """
    try:
        workbook, contents = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sheets_to_process = _resolve_sheets(workbook, sheet_names, import_all_sheets)

    try:
        return await import_workbook_oneshot(
            workbook, contents, file.filename or "unknown.xlsx",
            sheets_to_process, org_id, user_id, db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _resolve_sheets(workbook, sheet_names: Optional[List[str]], import_all: bool) -> List[str]:
    all_names = workbook.sheetnames
    if import_all:
        return all_names
    if sheet_names:
        valid = [s for s in sheet_names if s in all_names]
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"None of the requested sheets found. Available: {', '.join(all_names)}",
            )
        return valid
    return all_names
