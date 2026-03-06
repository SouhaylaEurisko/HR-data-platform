from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Candidate
from ..schemas import CandidateListResponse, CandidateRead
from datetime import date, datetime

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("/", response_model=CandidateListResponse)
def list_candidates(
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
    query = select(Candidate)


    if nationality:
        query = query.where(Candidate.nationality.ilike(f"%{nationality}%"))
    if date_of_birth:
        query = query.where(Candidate.date_of_birth == date_of_birth)
    if position:
        query = query.where(Candidate.position.ilike(f"%{position}%"))
    if expected_salary:
        query = query.where(Candidate.expected_salary == expected_salary)
    if current_address:
        query = query.where(Candidate.current_address.ilike(f"%{current_address}%"))
    if min_years_experience is not None:
        query = query.where(Candidate.years_experience >= min_years_experience)
    if max_years_experience is not None:
        query = query.where(Candidate.years_experience <= max_years_experience)
    if search:
        pattern = f"%{search}%"
        query = query.where(Candidate.full_name.ilike(pattern))

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0  # type: ignore[arg-type]

    sort_col = {
        "created_at": Candidate.created_at,
        "expected_salary": Candidate.expected_salary,
        "years_experience": Candidate.years_experience,
    }[sort_by]

    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    results = db.execute(query).scalars().all()

    return CandidateListResponse(
        items=[CandidateRead.model_validate(candidate) for candidate in results],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )
    return CandidateRead.model_validate(candidate)


