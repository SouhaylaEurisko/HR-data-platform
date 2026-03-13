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
    nationality: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    position: Optional[str] = None,
    expected_salary: Optional[float] = None,
    current_address: Optional[str] = None,
    min_years_experience: Optional[float] = Query(default=None, ge=0),
    max_years_experience: Optional[float] = Query(default=None, ge=0),
    search: Optional[str] = None,
    sort_by: Literal["created_at", "expected_salary", "years_experience"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    return list_candidates(
        db,
        page=page,
        page_size=page_size,
        nationality=nationality,
        date_of_birth=date_of_birth,
        position=position,
        expected_salary=expected_salary,
        current_address=current_address,
        min_years_experience=min_years_experience,
        max_years_experience=max_years_experience,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate_endpoint(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> CandidateRead:
    result = get_candidate_by_id(db, candidate_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return result
