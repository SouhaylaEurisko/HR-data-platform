"""
Router: Candidate listing and detail endpoints.

List query params: search by full name, position filter, sort/pagination.
"""

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.user import UserAccount
from ..routers.auth import get_current_user, require_hr_manager
from ..models import (
    CandidateApplicationStatusResponse,
    CandidateApplicationStatusUpdate,
    CandidateHrStageCommentCreate,
    CandidateHrStageCommentsUpdateResponse,
    CandidateProfileListResponse,
    CandidateProfilePatchResponse,
    CandidateRead,
    CandidateUpdate,
)
from ..services.candidate_service import (
    append_candidate_hr_stage_comment,
    delete_candidate_profile,
    get_candidate_by_id,
    list_candidate_profiles,
    update_candidate_application_status,
    update_candidate_profile,
)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateProfileListResponse)
def list_candidates_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: int = Query(1, description="Organization ID"),
    search: Optional[str] = None,
    applied_position: Optional[str] = None,
    sort_by: Literal[
        "created_at", "full_name", "email", "date_of_birth", "applied_position"
    ] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    _current_user: Annotated[UserAccount, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
) -> CandidateProfileListResponse:
    return list_candidate_profiles(
        db,
        org_id=org_id,
        page=page,
        page_size=page_size,
        search=search,
        applied_position=applied_position,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/{candidate_id}/hr-stage-comments", response_model=CandidateHrStageCommentsUpdateResponse)
def post_candidate_hr_stage_comment(
    candidate_id: int,
    body: CandidateHrStageCommentCreate,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateHrStageCommentsUpdateResponse:
    require_hr_manager(current_user)
    result = append_candidate_hr_stage_comment(db, candidate_id, org_id=org_id, body=body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result


@router.patch("/{candidate_id}/application-status", response_model=CandidateApplicationStatusResponse)
def patch_candidate_application_status(
    candidate_id: int,
    body: CandidateApplicationStatusUpdate,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateApplicationStatusResponse:
    require_hr_manager(current_user)
    result = update_candidate_application_status(db, candidate_id, org_id=org_id, body=body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result


@router.patch(
    "/{candidate_id}",
    response_model=CandidateProfilePatchResponse,
    response_model_exclude_unset=True,
)
def patch_candidate_endpoint(
    candidate_id: int,
    body: CandidateUpdate,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateProfilePatchResponse:
    require_hr_manager(current_user)
    result = update_candidate_profile(db, candidate_id, org_id=org_id, body=body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate_endpoint(
    candidate_id: int,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> None:
    require_hr_manager(current_user)
    applied = delete_candidate_profile(db, candidate_id, org_id=org_id)
    if not applied:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate_endpoint(
    candidate_id: int,
    org_id: int = Query(1, description="Organization ID"),
    _current_user: Annotated[UserAccount, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
) -> CandidateRead:
    result = get_candidate_by_id(db, candidate_id, org_id=org_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result
