"""
Router: Candidate resume — upload, view metadata, download PDF, delete.
"""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from ..constants import ResumeUpload
from ..schemas.resume import CandidateResumeRead
from ..models.user import UserAccount
from ..dependencies.auth import get_current_user, require_hr_manager
from ..dependencies.services import get_resume_service
from ..services.resume_service import ResumeServiceProtocol

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
    resume_service: ResumeServiceProtocol = Depends(get_resume_service),
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
        return await resume_service.upload_resume(
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


@router.get(
    "",
    response_model=CandidateResumeRead,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No resume for this candidate."}},
)
def get_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    resume_service: ResumeServiceProtocol = Depends(get_resume_service),
) -> CandidateResumeRead | Response:
    result = resume_service.get_resume(candidate_id, org_id=org_id)
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return result


@router.get("/download")
def download_candidate_resume(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    resume_service: ResumeServiceProtocol = Depends(get_resume_service),
):
    resume = resume_service.get_resume_file(candidate_id, org_id=org_id)
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
    resume_service: ResumeServiceProtocol = Depends(get_resume_service),
):
    require_hr_manager(current_user)
    deleted = resume_service.delete_resume(candidate_id, org_id=org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this candidate.",
        )
