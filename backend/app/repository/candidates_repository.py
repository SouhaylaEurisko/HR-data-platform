"""Candidate profile, application, and stage-comment queries."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased
from sqlalchemy.orm.attributes import flag_modified

from ..models.applications import Application
from ..models.candidate_stage_comment import CandidateStageComment
from ..models.candidates import CandidateProfile


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
    nationality_explicit: bool,
    nationality_value: Optional[str],
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

    need_application = bool(application_updates) or nationality_explicit
    application = get_latest_application_for_candidate(db, candidate.id)
    if application is None and need_application:
        application = Application(
            candidate_id=candidate.id,
            import_session_id=candidate.import_session_id,
        )
        db.add(application)
        db.flush()

    if application is not None:
        if nationality_explicit:
            cf = dict(application.custom_fields or {})
            if nationality_value is not None and str(nationality_value).strip() != "":
                cf["nationality"] = str(nationality_value).strip()
            else:
                cf.pop("nationality", None)
            application.custom_fields = cf
            flag_modified(application, "custom_fields")

        for key, value in application_updates.items():
            setattr(application, key, value)

    db.commit()
    db.refresh(candidate)
    if application is not None:
        db.refresh(application)
    return True
