"""
Router: XLSX upload, preview, and import endpoints.
All business logic lives in services/import_service.py.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..services.import_service import (
    load_workbook_from_file,
    preview_workbook,
    import_workbook,
)

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/xlsx/preview", summary="Preview XLSX file structure")
async def preview_xlsx(file: UploadFile = File(...)) -> dict:
    """Preview an XLSX file structure without importing."""
    try:
        workbook = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return preview_workbook(workbook, file.filename or "unknown.xlsx")


@router.post("/xlsx", summary="Upload and import an XLSX file")
async def import_xlsx(
    file: UploadFile = File(...),
    sheet_names: Optional[List[str]] = Query(None, description="Specific sheet names to import"),
    import_all_sheets: bool = Query(False, description="Import all sheets in the workbook"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Accepts an XLSX file and imports candidate data from one or more sheets.

    - By default, imports **all sheets** when no specific selection is provided.
    - Use `import_all_sheets=true` to explicitly import all sheets.
    - Use `sheet_names` query parameter to import specific sheets.
    """
    try:
        workbook = await load_workbook_from_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        return import_workbook(
            workbook=workbook,
            filename=file.filename or "unknown.xlsx",
            sheet_names=sheet_names,
            import_all_sheets=import_all_sheets,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
