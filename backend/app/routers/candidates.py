"""
Router: Candidate listing and detail endpoints.
"""

from typing import Literal, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models import CandidateListResponse, CandidateRead
from ..services.candidate_service import list_candidates, get_candidate_by_id

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
def list_candidates_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: int = Query(1, description="Organization ID"),
    nationality: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    applied_position: Optional[str] = None,
    current_address: Optional[str] = None,
    min_years_experience: Optional[float] = Query(default=None, ge=0),
    max_years_experience: Optional[float] = Query(default=None, ge=0),
    min_salary: Optional[float] = Query(default=None, ge=0),
    max_salary: Optional[float] = Query(default=None, ge=0),
    workplace_type_id: Optional[int] = None,
    employment_type_id: Optional[int] = None,
    is_employed: Optional[bool] = None,
    education_level_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Literal[
        "created_at", "current_salary", "expected_salary_remote", "expected_salary_onsite",
        "years_of_experience", "full_name", "applied_position",
    ] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    return list_candidates(
        db,
        org_id=org_id,
        page=page,
        page_size=page_size,
        nationality=nationality,
        date_of_birth=date_of_birth,
        applied_position=applied_position,
        current_address=current_address,
        min_years_experience=min_years_experience,
        max_years_experience=max_years_experience,
        min_salary=min_salary,
        max_salary=max_salary,
        workplace_type_id=workplace_type_id,
        employment_type_id=employment_type_id,
        is_employed=is_employed,
        education_level_id=education_level_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


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
