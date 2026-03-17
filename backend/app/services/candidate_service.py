"""
Candidate service — business logic for candidate listing and detail.
"""

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..models.candidate import Candidate, CandidateRead, CandidateListResponse


def list_candidates(
    db: Session,
    org_id: int = 1,
    page: int = 1,
    page_size: int = 20,
    nationality: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    applied_position: Optional[str] = None,
    current_address: Optional[str] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
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
) -> CandidateListResponse:
    query = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.residency_type),
            joinedload(Candidate.marital_status),
            joinedload(Candidate.passport_validity_status),
            joinedload(Candidate.workplace_type),
            joinedload(Candidate.employment_type),
            joinedload(Candidate.education_level),
            joinedload(Candidate.education_completion_status),
        )
        .filter(Candidate.organization_id == org_id)
    )

    if nationality:
        query = query.filter(Candidate.nationality.ilike(f"%{nationality}%"))
    if date_of_birth:
        query = query.filter(Candidate.date_of_birth == date_of_birth)
    if applied_position:
        query = query.filter(Candidate.applied_position.ilike(f"%{applied_position}%"))
    if current_address:
        query = query.filter(Candidate.current_address.ilike(f"%{current_address}%"))
    if min_years_experience is not None:
        query = query.filter(Candidate.years_of_experience >= Decimal(str(min_years_experience)))
    if max_years_experience is not None:
        query = query.filter(Candidate.years_of_experience <= Decimal(str(max_years_experience)))
    if min_salary is not None:
        query = query.filter(Candidate.current_salary >= Decimal(str(min_salary)))
    if max_salary is not None:
        query = query.filter(Candidate.current_salary <= Decimal(str(max_salary)))
    if workplace_type_id is not None:
        query = query.filter(Candidate.workplace_type_id == workplace_type_id)
    if employment_type_id is not None:
        query = query.filter(Candidate.employment_type_id == employment_type_id)
    if is_employed is not None:
        query = query.filter(Candidate.is_employed == is_employed)
    if education_level_id is not None:
        query = query.filter(Candidate.education_level_id == education_level_id)
    if search:
        query = query.filter(
            or_(
                Candidate.full_name.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%"),
            )
        )

    total = query.count()

    sort_column = getattr(Candidate, sort_by, Candidate.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()

    items = [CandidateRead.from_orm_with_lookups(c) for c in candidates]

    return CandidateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_candidate_by_id(db: Session, candidate_id: int, org_id: int = 1) -> Optional[CandidateRead]:
    candidate = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.residency_type),
            joinedload(Candidate.marital_status),
            joinedload(Candidate.passport_validity_status),
            joinedload(Candidate.workplace_type),
            joinedload(Candidate.employment_type),
            joinedload(Candidate.education_level),
            joinedload(Candidate.education_completion_status),
            joinedload(Candidate.import_session),
        )
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    import_filename = candidate.import_session.original_filename if candidate.import_session else None
    return CandidateRead.from_orm_with_lookups(candidate, import_filename=import_filename)
