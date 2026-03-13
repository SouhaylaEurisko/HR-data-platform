"""
Candidate service — business logic for candidate operations.
"""
from datetime import date
from typing import Literal, Optional
from math import ceil

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.candidate import Candidate, CandidateRead, CandidateListResponse


def list_candidates(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    nationality: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    position: Optional[str] = None,
    expected_salary: Optional[float] = None,
    current_address: Optional[str] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Literal["created_at", "expected_salary", "years_experience"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> CandidateListResponse:
    """
    List candidates with filtering, pagination, and sorting.
    
    Returns:
        CandidateListResponse with paginated results
    """
    # Start with base query
    query = db.query(Candidate)
    
    # Apply filters
    if nationality:
        query = query.filter(Candidate.nationality.ilike(f"%{nationality}%"))
    
    if date_of_birth:
        query = query.filter(Candidate.date_of_birth == date_of_birth)
    
    if position:
        query = query.filter(Candidate.position.ilike(f"%{position}%"))
    
    if expected_salary is not None:
        query = query.filter(Candidate.expected_salary == expected_salary)
    
    if current_address:
        query = query.filter(Candidate.current_address.ilike(f"%{current_address}%"))
    
    if min_years_experience is not None:
        query = query.filter(Candidate.years_experience >= min_years_experience)
    
    if max_years_experience is not None:
        query = query.filter(Candidate.years_experience <= max_years_experience)
    
    # Search by full_name or email
    if search:
        query = query.filter(
            or_(
                Candidate.full_name.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%")
            )
        )
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(Candidate, sort_by)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()
    
    # Convert to Pydantic models using from_orm_with_source if available
    candidate_reads = []
    for c in candidates:
        try:
            # Try to use from_orm_with_source to include source info
            candidate_read = CandidateRead.from_orm_with_source(c)
        except (AttributeError, KeyError):
            # Fallback to regular model_validate if relationship not loaded
            candidate_read = CandidateRead.model_validate(c)
        candidate_reads.append(candidate_read)
    
    return CandidateListResponse(
        items=candidate_reads,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_candidate_by_id(db: Session, candidate_id: int) -> Optional[CandidateRead]:
    """
    Get a single candidate by ID.
    
    Args:
        db: Database session
        candidate_id: Candidate ID
        
    Returns:
        CandidateRead if found, None otherwise
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if candidate is None:
        return None
    
    try:
        # Try to use from_orm_with_source to include source info
        return CandidateRead.from_orm_with_source(candidate)
    except (AttributeError, KeyError):
        # Fallback to regular model_validate if relationship not loaded
        return CandidateRead.model_validate(candidate)
