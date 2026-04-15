"""
Router: Candidate resume — upload, view metadata, download PDF, delete.
"""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import get_db
from ..constants import ResumeUpload
from ..schemas.resume import CandidateResumeRead
from ..models.user import UserAccount
from ..routers.auth import get_current_user, require_hr_manager
from ..services.resume_service import (
    delete_resume,
    get_resume,
    get_resume_file,
    upload_resume,
)

router = APIRouter(
    prefix="/api/candidates/{candidate_id}/resume",
    tags=["resume"],
)

@router.post("", response_model=CandidateResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    file: UploadFile = File(...),
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateResumeRead:
    require_hr_manager(current_user)

    if file.content_type not in ResumeUpload.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return await upload_resume(
            db=db,
            candidate_id=candidate_id,
            org_id=org_id,
            filename=file.filename or "resume.pdf",
            content_type=file.content_type or "application/pdf",
            file_data=file_data,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=CandidateResumeRead)
def get_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateResumeRead:
    result = get_resume(db, candidate_id, org_id=org_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this candidate.",
        )
    return result


@router.get("/download")
def download_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
):
    resume = get_resume_file(db, candidate_id, org_id=org_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this candidate.",
        )
    return StreamingResponse(
        BytesIO(resume.file_data),
        media_type=resume.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{resume.filename}"',
        },
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
):
    require_hr_manager(current_user)
    deleted = delete_resume(db, candidate_id, org_id=org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this candidate.",
        )
