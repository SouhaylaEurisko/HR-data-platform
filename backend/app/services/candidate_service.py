"""
Candidate service — listing and detail with org-scoped filters and eager loading.

HTTP list endpoint exposes name + position only; optional kwargs support chat-rich filters.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy.orm import Session, joinedload

from ..models.candidate import Candidate, CandidateListResponse, CandidateRead

_LOOKUP_EAGER_LIST = (
    joinedload(Candidate.residency_type),
    joinedload(Candidate.marital_status),
    joinedload(Candidate.passport_validity_status),
    joinedload(Candidate.workplace_type),
    joinedload(Candidate.employment_type),
    joinedload(Candidate.education_level),
    joinedload(Candidate.education_completion_status),
)

_LOOKUP_EAGER_DETAIL = _LOOKUP_EAGER_LIST + (joinedload(Candidate.import_session),)

# Sortable columns exposed on the candidates table (and created_at default)
SortBy = Literal[
    "created_at",
    "full_name",
    "applied_position",
    "current_salary",
    "expected_salary_remote",
    "expected_salary_onsite",
    "years_of_experience",
]

_SORT_COLUMNS: dict[str, object] = {
    "created_at": Candidate.created_at,
    "full_name": Candidate.full_name,
    "applied_position": Candidate.applied_position,
    "current_salary": Candidate.current_salary,
    "expected_salary_remote": Candidate.expected_salary_remote,
    "expected_salary_onsite": Candidate.expected_salary_onsite,
    "years_of_experience": Candidate.years_of_experience,
}


def _dec(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class _ListFilters:
    """Internal: HTTP passes name+position; chat may pass additional bounds."""
    search: Optional[str] = None
    applied_position: Optional[str] = None
    email: Optional[str] = None
    nationality: Optional[str] = None
    min_years_experience: Optional[float] = None
    max_years_experience: Optional[float] = None
    min_expected_salary_remote: Optional[float] = None
    max_expected_salary_remote: Optional[float] = None
    min_expected_salary_onsite: Optional[float] = None
    max_expected_salary_onsite: Optional[float] = None


def _base_query_for_org(db: Session, org_id: int):
    return db.query(Candidate).filter(Candidate.organization_id == org_id)


def _apply_filters(q, f: _ListFilters):
    if f.search:
        term = f"%{f.search.strip()}%"
        q = q.filter(Candidate.full_name.ilike(term))
    if f.applied_position:
        q = q.filter(Candidate.applied_position.ilike(f"%{f.applied_position.strip()}%"))
    if f.email:
        q = q.filter(Candidate.email.ilike(f"%{f.email.strip()}%"))
    if f.nationality:
        q = q.filter(Candidate.nationality.ilike(f"%{f.nationality.strip()}%"))
    lo = _dec(f.min_years_experience)
    if lo is not None:
        q = q.filter(Candidate.years_of_experience >= lo)
    hi = _dec(f.max_years_experience)
    if hi is not None:
        q = q.filter(Candidate.years_of_experience <= hi)
    rmin = _dec(f.min_expected_salary_remote)
    if rmin is not None:
        q = q.filter(Candidate.expected_salary_remote >= rmin)
    rmax = _dec(f.max_expected_salary_remote)
    if rmax is not None:
        q = q.filter(Candidate.expected_salary_remote <= rmax)
    omin = _dec(f.min_expected_salary_onsite)
    if omin is not None:
        q = q.filter(Candidate.expected_salary_onsite >= omin)
    omax = _dec(f.max_expected_salary_onsite)
    if omax is not None:
        q = q.filter(Candidate.expected_salary_onsite <= omax)
    return q


def list_candidates(
    db: Session,
    *,
    org_id: int = 1,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    applied_position: Optional[str] = None,
    email: Optional[str] = None,
    nationality: Optional[str] = None,
    min_years_experience: Optional[float] = None,
    max_years_experience: Optional[float] = None,
    min_expected_salary_remote: Optional[float] = None,
    max_expected_salary_remote: Optional[float] = None,
    min_expected_salary_onsite: Optional[float] = None,
    max_expected_salary_onsite: Optional[float] = None,
    sort_by: SortBy = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> CandidateListResponse:
    """
    Paginated list. Router passes name (search) + position only; chat passes extra kwargs.
    """
    def _s(v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    flt = _ListFilters(
        search=_s(search),
        applied_position=_s(applied_position),
        email=_s(email),
        nationality=_s(nationality),
        min_years_experience=min_years_experience,
        max_years_experience=max_years_experience,
        min_expected_salary_remote=min_expected_salary_remote,
        max_expected_salary_remote=max_expected_salary_remote,
        min_expected_salary_onsite=min_expected_salary_onsite,
        max_expected_salary_onsite=max_expected_salary_onsite,
    )

    count_q = _apply_filters(_base_query_for_org(db, org_id), flt)
    total = count_q.count()

    sort_col = _SORT_COLUMNS.get(sort_by, Candidate.created_at)
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    offset = (page - 1) * page_size

    data_q = (
        _apply_filters(
            db.query(Candidate).options(*_LOOKUP_EAGER_LIST).filter(Candidate.organization_id == org_id),
            flt,
        )
        .order_by(order)
        .offset(offset)
        .limit(page_size)
    )
    rows = data_q.all()
    items = [CandidateRead.from_orm_with_lookups(c) for c in rows]

    return CandidateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def update_candidate_hr_comment(
    db: Session,
    candidate_id: int,
    org_id: int,
    hr_comment: str,
) -> Optional[CandidateRead]:
    """Set or clear HR comment (empty string → NULL). Not used by import."""
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    text = hr_comment.strip() if hr_comment else ""
    candidate.hr_comment = text if text else None
    db.commit()
    db.refresh(candidate)
    return get_candidate_by_id(db, candidate_id, org_id=org_id)


def get_candidate_by_id(
    db: Session,
    candidate_id: int,
    org_id: int = 1,
) -> Optional[CandidateRead]:
    """Single candidate scoped to organization, with lookups and import filename."""
    candidate = (
        db.query(Candidate)
        .options(*_LOOKUP_EAGER_DETAIL)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    import_filename = (
        candidate.import_session.original_filename if candidate.import_session else None
    )
    return CandidateRead.from_orm_with_lookups(candidate, import_filename=import_filename)
