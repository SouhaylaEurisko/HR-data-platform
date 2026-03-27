"""
Org-scoped analytics — SQL aggregations on candidate (+ resume) data.
No LLM; safe for HR viewers (router enforces auth + org from JWT user).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.analytics import (
    AnalyticsAppliedFilters,
    AnalyticsFilterOption,
    AnalyticsFilterOptions,
    AnalyticsOverviewResponse,
    NamedCount,
    PositionAverageMetric,
)
from ..models.candidate import Candidate
from ..models.candidate_resume import CandidateResume

UNSET_FILTER_VALUE = "__unset__"

_STATUS_LABELS = {
    "pending": "Pending",
    "on_hold": "On hold",
    "rejected": "Rejected",
    "selected": "Selected",
}


@dataclass(frozen=True, slots=True)
class _AnalyticsFilters:
    status: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None


def _named_counts(rows: list[tuple[str | None, int]], *, empty_label: str = "Unknown") -> List[NamedCount]:
    out: List[NamedCount] = []
    for name, cnt in rows:
        label = (name or "").strip() or empty_label
        out.append(NamedCount(name=label, count=int(cnt)))
    return out


def _clean_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _blank_or_null(column):
    return or_(column.is_(None), func.btrim(column) == "")


def _apply_string_filter(query, column, value: Optional[str]):
    if value is None:
        return query
    if value == UNSET_FILTER_VALUE:
        return query.filter(_blank_or_null(column))
    return query.filter(func.lower(func.btrim(column)) == value.lower())


def _apply_analytics_filters(query, filters: _AnalyticsFilters):
    query = _apply_string_filter(query, Candidate.application_status, filters.status)
    query = _apply_string_filter(query, Candidate.applied_position, filters.position)
    query = _apply_string_filter(query, Candidate.applied_position_location, filters.location)
    return query


def _build_filter_options(
    db: Session,
    organization_id: int,
    column,
    *,
    empty_label: str = "Not set",
    label_map: Optional[dict[str, str]] = None,
) -> List[AnalyticsFilterOption]:
    value_expr = func.nullif(func.btrim(column), "")
    rows = (
        db.query(value_expr, func.count(Candidate.id))
        .filter(Candidate.organization_id == organization_id)
        .group_by(value_expr)
        .order_by(func.count(Candidate.id).desc(), value_expr.asc())
        .all()
    )

    options: List[AnalyticsFilterOption] = []
    for raw_value, count in rows:
        if raw_value is None:
            options.append(
                AnalyticsFilterOption(
                    value=UNSET_FILTER_VALUE,
                    label=empty_label,
                    count=int(count),
                )
            )
            continue

        value = str(raw_value).strip()
        label = label_map.get(value.lower(), value) if label_map else value
        options.append(
            AnalyticsFilterOption(
                value=value,
                label=label,
                count=int(count),
            )
        )
    return options


def get_analytics_overview(
    db: Session,
    organization_id: int,
    *,
    status: Optional[str] = None,
    position: Optional[str] = None,
    location: Optional[str] = None,
) -> AnalyticsOverviewResponse:
    org = organization_id
    now = datetime.now(timezone.utc)
    filters = _AnalyticsFilters(
        status=_clean_filter(status),
        position=_clean_filter(position),
        location=_clean_filter(location),
    )

    total = (
        _apply_analytics_filters(
            db.query(func.count(Candidate.id)).filter(Candidate.organization_id == org),
            filters,
        )
        .scalar()
        or 0
    )

    status_key = func.coalesce(
        func.nullif(func.btrim(Candidate.application_status), ""),
        "unset",
    )
    status_rows = (
        _apply_analytics_filters(
            db.query(status_key, func.count(Candidate.id)).filter(Candidate.organization_id == org),
            filters,
        )
        .group_by(status_key)
        .order_by(func.count(Candidate.id).desc())
        .all()
    )
    by_status = [NamedCount(name=str(r[0]), count=int(r[1])) for r in status_rows]

    pos_rows = (
        _apply_analytics_filters(
            db.query(Candidate.applied_position, func.count(Candidate.id)).filter(
                Candidate.organization_id == org,
                Candidate.applied_position.isnot(None),
                func.btrim(Candidate.applied_position) != "",
            ),
            filters,
        )
        .group_by(Candidate.applied_position)
        .order_by(func.count(Candidate.id).desc())
        .limit(10)
        .all()
    )
    top_positions = _named_counts(pos_rows, empty_label="Unknown")

    loc_rows = (
        _apply_analytics_filters(
            db.query(Candidate.applied_position_location, func.count(Candidate.id)).filter(
                Candidate.organization_id == org,
                Candidate.applied_position_location.isnot(None),
                func.btrim(Candidate.applied_position_location) != "",
            ),
            filters,
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
        _apply_analytics_filters(
            db.query(
                Candidate.applied_position,
                func.avg(salary_expr),
                func.count(Candidate.id),
            ).filter(
                Candidate.organization_id == org,
                Candidate.applied_position.isnot(None),
                func.btrim(Candidate.applied_position) != "",
                or_(
                    Candidate.expected_salary_remote.isnot(None),
                    Candidate.expected_salary_onsite.isnot(None),
                ),
            ),
            filters,
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
        _apply_analytics_filters(
            db.query(
                Candidate.applied_position,
                func.avg(Candidate.years_of_experience),
                func.count(Candidate.id),
            ).filter(
                Candidate.organization_id == org,
                Candidate.applied_position.isnot(None),
                func.btrim(Candidate.applied_position) != "",
                Candidate.years_of_experience.isnot(None),
            ),
            filters,
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
        _apply_analytics_filters(
            db.query(func.count(Candidate.id))
            .join(CandidateResume, CandidateResume.candidate_id == Candidate.id)
            .filter(
                Candidate.organization_id == org,
                CandidateResume.organization_id == org,
            ),
            filters,
        )
        .scalar()
        or 0
    )

    pct_resume = round(100.0 * with_resume / total, 1) if total else 0.0

    since = now - timedelta(days=30)
    recent = (
        _apply_analytics_filters(
            db.query(func.count(Candidate.id)).filter(
                Candidate.organization_id == org,
                Candidate.created_at >= since,
            ),
            filters,
        )
        .scalar()
        or 0
    )

    filter_options = AnalyticsFilterOptions(
        statuses=_build_filter_options(
            db,
            org,
            Candidate.application_status,
            empty_label="Not set",
            label_map=_STATUS_LABELS,
        ),
        positions=_build_filter_options(
            db,
            org,
            Candidate.applied_position,
            empty_label="Not set",
        ),
        locations=_build_filter_options(
            db,
            org,
            Candidate.applied_position_location,
            empty_label="Not set",
        ),
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
        filter_options=filter_options,
        applied_filters=AnalyticsAppliedFilters(
            status=filters.status,
            position=filters.position,
            location=filters.location,
        ),
    )
