"""
Router: Candidate listing and detail endpoints.

List query params: search by full name, position filter, sort/pagination.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models import CandidateHrCommentUpdate, CandidateListResponse, CandidateRead
from ..services.candidate_service import (
    get_candidate_by_id,
    list_candidates,
    update_candidate_hr_comment,
)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
def list_candidates_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: int = Query(1, description="Organization ID"),
    search: Optional[str] = None,
    applied_position: Optional[str] = None,
    sort_by: Literal[
        "created_at",
        "full_name",
        "applied_position",
        "years_of_experience",
        "expected_salary_remote",
        "expected_salary_onsite",
    ] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    return list_candidates(
        db,
        org_id=org_id,
        page=page,
        page_size=page_size,
        search=search,
        applied_position=applied_position,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.patch("/{candidate_id}/hr-comment", response_model=CandidateRead)
def patch_candidate_hr_comment(
    candidate_id: int,
    body: CandidateHrCommentUpdate,
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateRead:
    result = update_candidate_hr_comment(
        db, candidate_id, org_id=org_id, hr_comment=body.hr_comment
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate_endpoint(
    candidate_id: int,
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> CandidateRead:
    result = get_candidate_by_id(db, candidate_id, org_id=org_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result
