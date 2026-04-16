"""
Candidate service — listing and detail with org-scoped filters and eager loading.

HTTP list endpoint exposes name + position only; optional kwargs support chat-rich filters.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from ..models.candidate import (
    Candidate,
    CandidateApplicationStatusUpdate,
    CandidateListResponse,
    CandidatePersonalUpdate,
    CandidateProfessionalUpdate,
    CandidateRead,
    RelatedApplicationSummary,
)
from ..models.candidate_stage_comment import (
    CandidateHrStageCommentCreate,
    CandidateStageComment,
    empty_hr_stage_comments_read,
)
from .candidate_stage_comments import (
    fetch_hr_stage_comments_for_candidate,
    fetch_hr_stage_comments_for_candidate_ids,
)

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


def _application_context_for_candidate(
    db: Session,
    *,
    org_id: int,
    candidate_id: int,
    email: Optional[str],
) -> tuple[Optional[int], Optional[int], list[RelatedApplicationSummary]]:
    """
    Group applications by same email (case-insensitive, trimmed) within the org.
    Order: applied_at (oldest first), then created_at, then id.
    """
    if not email or not str(email).strip():
        return None, None, []
    norm = str(email).strip().lower()
    rows = (
        db.query(Candidate.id, Candidate.applied_position, Candidate.applied_at, Candidate.created_at)
        .filter(
            Candidate.organization_id == org_id,
            Candidate.email.isnot(None),
            func.lower(func.trim(Candidate.email)) == norm,
        )
        .order_by(
            Candidate.applied_at.asc().nulls_last(),
            Candidate.created_at.asc(),
            Candidate.id.asc(),
        )
        .all()
    )
    if not rows:
        return None, None, []
    related = [
        RelatedApplicationSummary(
            id=r.id,
            applied_position=r.applied_position,
            applied_at=r.applied_at,
            created_at=r.created_at,
        )
        for r in rows
    ]
    ids = [r.id for r in rows]
    try:
        idx_1based = ids.index(candidate_id) + 1
    except ValueError:
        return None, None, related
    return idx_1based, len(rows), related


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
    ids = [c.id for c in rows]
    latest_by_id = fetch_hr_stage_comments_for_candidate_ids(
        db, org_id=org_id, candidate_ids=ids, latest_only=True
    )
    items = [
        CandidateRead.from_orm_with_lookups(
            c,
            hr_stage_comments=latest_by_id.get(c.id, empty_hr_stage_comments_read()),
        )
        for c in rows
    ]

    return CandidateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def append_candidate_hr_stage_comment(
    db: Session,
    candidate_id: int,
    org_id: int,
    body: CandidateHrStageCommentCreate,
) -> Optional[CandidateRead]:
    """Append one object to the JSONB `entries` array for (candidate, stage)."""
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_item = {"text": body.text, "created_at": now}
    existing = (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.stage_key == body.stage,
        )
        .with_for_update()
        .first()
    )
    if existing:
        entries = list(existing.entries) if isinstance(existing.entries, list) else []
        entries.append(new_item)
        existing.entries = entries
        flag_modified(existing, "entries")
    else:
        db.add(
            CandidateStageComment(
                candidate_id=candidate_id,
                organization_id=org_id,
                stage_key=body.stage,
                entries=[new_item],
            )
        )
    db.commit()
    return get_candidate_by_id(db, candidate_id, org_id=org_id)


def update_candidate_application_status(
    db: Session,
    candidate_id: int,
    org_id: int,
    body: CandidateApplicationStatusUpdate,
) -> Optional[CandidateRead]:
    """Set application status (UI only); independent from HR stage comments."""
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    candidate.application_status = body.application_status.value
    db.commit()
    db.refresh(candidate)
    return get_candidate_by_id(db, candidate_id, org_id=org_id)


def update_candidate_personal(
    db: Session,
    candidate_id: int,
    org_id: int,
    body: CandidatePersonalUpdate,
) -> Optional[CandidateRead]:
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    return get_candidate_by_id(db, candidate_id, org_id=org_id)


def update_candidate_professional(
    db: Session,
    candidate_id: int,
    org_id: int,
    body: CandidateProfessionalUpdate,
) -> Optional[CandidateRead]:
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return None
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    return get_candidate_by_id(db, candidate_id, org_id=org_id)


def delete_candidate(db: Session, candidate_id: int, org_id: int) -> bool:
    """
    Remove candidate row; DB CASCADE removes candidate_resume and candidate_stage_comment rows.
    """
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.organization_id == org_id)
        .first()
    )
    if candidate is None:
        return False
    db.delete(candidate)
    db.commit()
    return True


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
    app_idx, app_total, related = _application_context_for_candidate(
        db,
        org_id=org_id,
        candidate_id=candidate_id,
        email=candidate.email,
    )
    hr_comments = fetch_hr_stage_comments_for_candidate(
        db, org_id=org_id, candidate_id=candidate_id
    )
    return CandidateRead.from_orm_with_lookups(
        candidate,
        hr_stage_comments=hr_comments,
        import_filename=import_filename,
        application_index=app_idx,
        application_total=app_total,
        related_applications=related,
    )
