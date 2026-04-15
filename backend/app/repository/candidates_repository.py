"""Candidate profile, application, and stage-comment queries."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy import func, nullslast
from sqlalchemy.orm import Session, aliased
from sqlalchemy.orm.attributes import flag_modified

from ..models.applications import Application
from ..models.candidate_stage_comment import CandidateStageComment
from ..models.candidates import CandidateProfile

_CHAT_LIST_SORT_COLUMNS: dict[str, Any] = {
    "created_at": CandidateProfile.created_at,
    "full_name": CandidateProfile.full_name,
}

_UI_LIST_SORT_COLUMNS: dict[str, Any] = {
    "created_at": CandidateProfile.created_at,
    "full_name": CandidateProfile.full_name,
    "email": CandidateProfile.email,
    "date_of_birth": CandidateProfile.date_of_birth,
}


@dataclass(frozen=True, slots=True)
class CandidateListFilterParams:
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


def _dec(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def profiles_base_query(db: Session, org_id: int):
    return db.query(CandidateProfile).filter(CandidateProfile.organization_id == org_id)


def apply_candidate_list_filters(q, db: Session, f: CandidateListFilterParams):
    def _apply_application_predicate(q0, predicate):
        return q0.filter(
            CandidateProfile.id.in_(db.query(Application.candidate_id).filter(predicate))
        )

    def _apply_application_range(q0, min_value, max_value, column):
        lo = _dec(min_value)
        if lo is not None:
            q0 = _apply_application_predicate(q0, column >= lo)
        hi = _dec(max_value)
        if hi is not None:
            q0 = _apply_application_predicate(q0, column <= hi)
        return q0

    if f.search:
        term = f"%{f.search.strip()}%"
        q = q.filter(CandidateProfile.full_name.ilike(term))
    if f.applied_position:
        q = _apply_application_predicate(
            q, Application.applied_position.ilike(f"%{f.applied_position.strip()}%")
        )
    if f.email:
        q = q.filter(CandidateProfile.email.ilike(f"%{f.email.strip()}%"))
    if f.nationality and str(f.nationality).strip():
        term = f"%{str(f.nationality).strip()}%"
        q = _apply_application_predicate(q, Application.nationality.ilike(term))
    q = _apply_application_range(
        q, f.min_years_experience, f.max_years_experience, Application.years_of_experience
    )
    q = _apply_application_range(
        q, f.min_expected_salary_remote, f.max_expected_salary_remote, Application.expected_salary_remote
    )
    q = _apply_application_range(
        q, f.min_expected_salary_onsite, f.max_expected_salary_onsite, Application.expected_salary_onsite
    )
    return q


def fetch_email_group_rows(
    db: Session,
    *,
    org_id: int,
    email_normalized: str,
) -> list[Any]:
    """
    Profiles in org with same email (trimmed lower), ordered for related-application UX.
    Returns ORM Row-like objects with .id, .applied_position, .applied_at, .created_at.
    """
    return (
        db.query(
            CandidateProfile.id,
            Application.applied_position,
            Application.applied_at,
            CandidateProfile.created_at,
        )
        .outerjoin(Application, Application.candidate_id == CandidateProfile.id)
        .filter(
            CandidateProfile.organization_id == org_id,
            CandidateProfile.email.isnot(None),
            func.lower(func.trim(CandidateProfile.email)) == email_normalized,
        )
        .order_by(
            Application.applied_at.asc().nulls_last(),
            CandidateProfile.created_at.asc(),
            CandidateProfile.id.asc(),
        )
        .all()
    )


def get_candidate_profile_by_id_org(
    db: Session, candidate_id: int, org_id: int
) -> Optional[CandidateProfile]:
    return (
        db.query(CandidateProfile)
        .filter(CandidateProfile.id == candidate_id, CandidateProfile.organization_id == org_id)
        .first()
    )


def get_latest_application_for_candidate(db: Session, candidate_id: int) -> Optional[Application]:
    return (
        db.query(Application)
        .filter(Application.candidate_id == candidate_id)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .first()
    )


def fetch_latest_application_status(
    db: Session, candidate_id: int, org_id: int
) -> Optional[str]:
    row = (
        db.query(CandidateStageComment.application_status)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.application_status.isnot(None),
            func.btrim(CandidateStageComment.application_status) != "",
        )
        .order_by(CandidateStageComment.updated_at.desc(), CandidateStageComment.id.desc())
        .first()
    )
    return row[0] if row else None


def query_profiles_for_list(
    db: Session,
    org_id: int,
    search: Optional[str],
    applied_position: Optional[str] = None,
):
    """List query: optional name search and applied-position filter (via applications subquery)."""
    params = CandidateListFilterParams(
        search=str(search).strip() if search and str(search).strip() else None,
        applied_position=str(applied_position).strip()
        if applied_position and str(applied_position).strip()
        else None,
    )
    return apply_candidate_list_filters(profiles_base_query(db, org_id), db, params)


def latest_applications_by_candidate_ids(
    db: Session, candidate_ids: List[int]
) -> Dict[int, Application]:
    """Latest application row per candidate_id (by max id among ties)."""
    if not candidate_ids:
        return {}
    subq = (
        db.query(
            Application.candidate_id.label("cid"),
            func.max(Application.id).label("mid"),
        )
        .filter(Application.candidate_id.in_(candidate_ids))
        .group_by(Application.candidate_id)
        .subquery()
    )
    apps = (
        db.query(Application)
        .join(
            subq,
            (Application.candidate_id == subq.c.cid) & (Application.id == subq.c.mid),
        )
        .all()
    )
    return {a.candidate_id: a for a in apps}


def latest_application_status_by_candidate_ids(
    db: Session, org_id: int, candidate_ids: List[int]
) -> Dict[int, str]:
    """
    Most recently updated non-empty application_status per candidate
    (across candidate_stage_comment rows).
    """
    if not candidate_ids:
        return {}
    rows = (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id.in_(candidate_ids),
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.application_status.isnot(None),
            func.btrim(CandidateStageComment.application_status) != "",
        )
        .order_by(
            CandidateStageComment.updated_at.desc(),
            CandidateStageComment.id.desc(),
        )
        .all()
    )
    out: Dict[int, str] = {}
    for r in rows:
        if r.candidate_id not in out and r.application_status:
            out[r.candidate_id] = str(r.application_status).strip()
    return out


def profiles_query_with_latest_application_join(db: Session, query):
    """Outer-join latest Application per profile for sorting by applied_position."""
    subq = (
        db.query(
            Application.candidate_id.label("cid"),
            func.max(Application.id).label("mid"),
        )
        .group_by(Application.candidate_id)
        .subquery()
    )
    LatestApp = aliased(Application)
    q = query.outerjoin(subq, CandidateProfile.id == subq.c.cid).outerjoin(
        LatestApp, LatestApp.id == subq.c.mid
    )
    return q, LatestApp


def get_stage_comment_for_update(
    db: Session, candidate_id: int, org_id: int, stage_key: str
) -> Optional[CandidateStageComment]:
    return (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
            CandidateStageComment.stage_key == stage_key,
        )
        .with_for_update()
        .first()
    )


def list_stage_comments_for_candidate(
    db: Session, candidate_id: int, org_id: int
) -> list[CandidateStageComment]:
    return (
        db.query(CandidateStageComment)
        .filter(
            CandidateStageComment.candidate_id == candidate_id,
            CandidateStageComment.organization_id == org_id,
        )
        .all()
    )


def fetch_filtered_candidates_page(
    db: Session,
    *,
    org_id: int,
    filters: CandidateListFilterParams,
    sort_by: str,
    sort_order: Literal["asc", "desc"],
    page: int,
    page_size: int,
) -> Tuple[int, List[CandidateProfile]]:
    """Count + page of profiles after list filters (chat / rich list)."""
    count_q = apply_candidate_list_filters(profiles_base_query(db, org_id), db, filters)
    total = count_q.count()
    sort_col = _CHAT_LIST_SORT_COLUMNS.get(sort_by, CandidateProfile.created_at)
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    offset = (page - 1) * page_size
    rows = (
        count_q.order_by(order, CandidateProfile.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return total, rows


def fetch_profile_list_page(
    db: Session,
    *,
    org_id: int,
    search: Optional[str],
    applied_position: Optional[str],
    sort_by: Literal[
        "created_at", "full_name", "email", "date_of_birth", "applied_position"
    ],
    sort_order: Literal["asc", "desc"],
    page: int,
    page_size: int,
) -> Tuple[int, List[CandidateProfile]]:
    """Count + page for HR UI candidate table (sort may join latest application)."""
    query = query_profiles_for_list(db, org_id, search, applied_position)
    if sort_by == "applied_position":
        query, LatestApp = profiles_query_with_latest_application_join(db, query)
        sort_col = LatestApp.applied_position
    else:
        sort_col = _UI_LIST_SORT_COLUMNS.get(sort_by, CandidateProfile.created_at)

    total = query.count()
    order = (
        nullslast(sort_col.asc())
        if sort_order == "asc"
        else nullslast(sort_col.desc())
    )
    offset = (page - 1) * page_size
    rows = (
        query.order_by(order, CandidateProfile.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return total, rows


def get_shared_email_application_context(
    db: Session,
    *,
    org_id: int,
    candidate_id: int,
    email: Optional[str],
) -> Tuple[Optional[int], Optional[int], List[Any]]:
    """
    Same-email siblings within org: 1-based index of candidate_id, total count, raw group rows.

    Rows match ``fetch_email_group_rows`` shape (id, applied_position, applied_at, created_at).
    """
    if not email or not str(email).strip():
        return None, None, []
    norm = str(email).strip().lower()
    rows = fetch_email_group_rows(db, org_id=org_id, email_normalized=norm)
    if not rows:
        return None, None, []
    ids = [r.id for r in rows]
    try:
        idx_1based = ids.index(candidate_id) + 1
    except ValueError:
        return None, None, list(rows)
    return idx_1based, len(rows), list(rows)


def append_hr_stage_comment_entry(
    db: Session,
    *,
    candidate_id: int,
    org_id: int,
    stage_key: str,
    text: str,
) -> bool:
    """Append one JSONB entry for (candidate, stage). Returns False if profile missing."""
    if get_candidate_profile_by_id_org(db, candidate_id, org_id) is None:
        return False
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_item = {"text": text, "created_at": now}
    existing = get_stage_comment_for_update(db, candidate_id, org_id, stage_key)
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
                stage_key=stage_key,
                entries=[new_item],
            )
        )
    db.commit()
    return True


def set_application_status_on_candidate_stage_comments(
    db: Session,
    *,
    candidate_id: int,
    org_id: int,
    status_value: str,
) -> bool:
    """Mirror application_status onto all stage-comment rows (or seed one row). False if no profile."""
    if get_candidate_profile_by_id_org(db, candidate_id, org_id) is None:
        return False
    stage_rows = list_stage_comments_for_candidate(db, candidate_id, org_id)
    if stage_rows:
        for row in stage_rows:
            row.application_status = status_value
    else:
        db.add(
            CandidateStageComment(
                candidate_id=candidate_id,
                organization_id=org_id,
                stage_key="pre_screening",
                entries=[],
                application_status=status_value,
            )
        )
    db.commit()
    return True


def delete_candidate_profile_for_org(db: Session, candidate_id: int, org_id: int) -> bool:
    """
    Remove a candidate profile scoped to org.

    Cascades (ORM / DB): applications, candidate_resume, candidate_stage_comment rows
    tied to this candidates.id are removed with the profile.
    """
    row = get_candidate_profile_by_id_org(db, candidate_id, org_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def persist_candidate_profile_patch(
    db: Session,
    *,
    candidate_id: int,
    org_id: int,
    profile_updates: Dict[str, Any],
    application_updates: Dict[str, Any],
) -> bool:
    """
    Apply profile + latest-application field writes and commit.

    ``has_transportation`` in *application_updates* must already be resolved to bool | None.
    """
    candidate = get_candidate_profile_by_id_org(db, candidate_id, org_id)
    if candidate is None:
        return False

    for key, value in profile_updates.items():
        setattr(candidate, key, value)

    need_application = bool(application_updates)
    application = get_latest_application_for_candidate(db, candidate.id)
    if application is None and need_application:
        application = Application(
            candidate_id=candidate.id,
            import_session_id=candidate.import_session_id,
        )
        db.add(application)
        db.flush()

    if application is not None:
        if "nationality" in application_updates:
            cf = dict(application.custom_fields or {})
            if "nationality" in cf:
                cf.pop("nationality")
                application.custom_fields = cf
                flag_modified(application, "custom_fields")

        for key, value in application_updates.items():
            setattr(application, key, value)

    db.commit()
    db.refresh(candidate)
    if application is not None:
        db.refresh(application)
    return True
