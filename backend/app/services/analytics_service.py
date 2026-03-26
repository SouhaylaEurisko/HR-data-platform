"""
Org-scoped analytics — SQL aggregations on candidate (+ resume) data.
No LLM; safe for HR viewers (router enforces auth + org from JWT user).
"""

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.analytics import AnalyticsOverviewResponse, NamedCount, PositionAverageMetric
from ..models.candidate import Candidate
from ..models.candidate_resume import CandidateResume


def _named_counts(rows: list[tuple[str | None, int]], *, empty_label: str = "Unknown") -> List[NamedCount]:
    out: List[NamedCount] = []
    for name, cnt in rows:
        label = (name or "").strip() or empty_label
        out.append(NamedCount(name=label, count=int(cnt)))
    return out


def get_analytics_overview(db: Session, organization_id: int) -> AnalyticsOverviewResponse:
    org = organization_id
    now = datetime.now(timezone.utc)

    total = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.organization_id == org)
        .scalar()
        or 0
    )

    status_key = func.coalesce(
        func.nullif(func.btrim(Candidate.application_status), ""),
        "unset",
    )
    status_rows = (
        db.query(status_key, func.count(Candidate.id))
        .filter(Candidate.organization_id == org)
        .group_by(status_key)
        .order_by(func.count(Candidate.id).desc())
        .all()
    )
    by_status = [NamedCount(name=str(r[0]), count=int(r[1])) for r in status_rows]

    pos_rows = (
        db.query(Candidate.applied_position, func.count(Candidate.id))
        .filter(
            Candidate.organization_id == org,
            Candidate.applied_position.isnot(None),
            func.btrim(Candidate.applied_position) != "",
        )
        .group_by(Candidate.applied_position)
        .order_by(func.count(Candidate.id).desc())
        .limit(10)
        .all()
    )
    top_positions = _named_counts(pos_rows, empty_label="Unknown")

    loc_rows = (
        db.query(Candidate.applied_position_location, func.count(Candidate.id))
        .filter(
            Candidate.organization_id == org,
            Candidate.applied_position_location.isnot(None),
            func.btrim(Candidate.applied_position_location) != "",
        )
        .group_by(Candidate.applied_position_location)
        .order_by(func.count(Candidate.id).desc())
        .limit(10)
        .all()
    )
    top_locations = _named_counts(loc_rows, empty_label="Unknown")

    # Expected salary: COALESCE(remote, onsite) per row; average per position (top 10 by headcount with data)
    salary_expr = func.coalesce(Candidate.expected_salary_remote, Candidate.expected_salary_onsite)
    salary_rows = (
        db.query(
            Candidate.applied_position,
            func.avg(salary_expr),
            func.count(Candidate.id),
        )
        .filter(
            Candidate.organization_id == org,
            Candidate.applied_position.isnot(None),
            func.btrim(Candidate.applied_position) != "",
            or_(
                Candidate.expected_salary_remote.isnot(None),
                Candidate.expected_salary_onsite.isnot(None),
            ),
        )
        .group_by(Candidate.applied_position)
        .order_by(func.count(Candidate.id).desc())
        .limit(10)
        .all()
    )
    avg_salary_by_pos = [
        PositionAverageMetric(
            name=(str(r[0]) or "").strip() or "Unknown",
            average=round(float(r[1]), 2) if r[1] is not None else 0.0,
            sample_count=int(r[2]),
        )
        for r in salary_rows
    ]

    yoe_rows = (
        db.query(
            Candidate.applied_position,
            func.avg(Candidate.years_of_experience),
            func.count(Candidate.id),
        )
        .filter(
            Candidate.organization_id == org,
            Candidate.applied_position.isnot(None),
            func.btrim(Candidate.applied_position) != "",
            Candidate.years_of_experience.isnot(None),
        )
        .group_by(Candidate.applied_position)
        .order_by(func.count(Candidate.id).desc())
        .limit(10)
        .all()
    )
    avg_yoe_by_pos = [
        PositionAverageMetric(
            name=(str(r[0]) or "").strip() or "Unknown",
            average=round(float(r[1]), 2) if r[1] is not None else 0.0,
            sample_count=int(r[2]),
        )
        for r in yoe_rows
    ]

    with_resume = (
        db.query(func.count(Candidate.id))
        .join(CandidateResume, CandidateResume.candidate_id == Candidate.id)
        .filter(
            Candidate.organization_id == org,
            CandidateResume.organization_id == org,
        )
        .scalar()
        or 0
    )

    pct_resume = round(100.0 * with_resume / total, 1) if total else 0.0

    since = now - timedelta(days=30)
    recent = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.organization_id == org, Candidate.created_at >= since)
        .scalar()
        or 0
    )

    return AnalyticsOverviewResponse(
        total_candidates=int(total),
        by_application_status=by_status,
        top_applied_positions=top_positions,
        top_locations=top_locations,
        avg_expected_salary_by_position=avg_salary_by_pos,
        avg_years_experience_by_position=avg_yoe_by_pos,
        candidates_with_resume=int(with_resume),
        resume_coverage_percent=pct_resume,
        recent_applications_30d=int(recent),
    )
