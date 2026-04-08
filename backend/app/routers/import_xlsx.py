"""
Router: XLSX upload — preview, analyze, and confirm (two-phase import).
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.user import UserAccount
from ..models.import_session import ConfirmImportRequest, DuplicateCheckRequest
from ..routers.auth import get_current_user, require_hr_manager
from ..services.import_service import (
    analyze_workbook,
    check_import_name_conflicts,
    confirm_and_import,
    load_workbook_from_file,
    preview_workbook,
)

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/xlsx/preview", summary="Preview Excel file structure")
async def preview_xlsx(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    require_hr_manager(current_user)
    try:
        workbook, _ = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return preview_workbook(workbook, file.filename or "unknown.xlsx")


@router.post("/xlsx/analyze", summary="Analyze Excel and suggest column mappings")
async def analyze_xlsx(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
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
    require_hr_manager(current_user)
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


@router.post("/xlsx/duplicate-check", summary="Check duplicate file/sheet names before import")
def check_xlsx_duplicate_names(
    body: DuplicateCheckRequest,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    require_hr_manager(current_user)
    return check_import_name_conflicts(
        db=db,
        org_id=body.org_id,
        filename=body.filename,
        sheet_names=body.sheet_names,
    )


@router.post("/xlsx/confirm", summary="Confirm column mappings and import")
def confirm_xlsx(
    body: ConfirmImportRequest,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Phase B of two-phase import.
    Receives confirmed column mappings from HR and imports the data.
    """
    require_hr_manager(current_user)
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
