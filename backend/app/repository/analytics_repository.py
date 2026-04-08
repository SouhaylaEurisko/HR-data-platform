"""
Org-scoped analytics — SQLAlchemy queries over applications, profiles, stage comments, resumes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.analytics import AnalyticsFilterOption, PositionAverageMetric
from ..models.applications import Application
from ..models.candidates import CandidateProfile
from ..models.candidate_stage_comment import CandidateStageComment
from ..models.candidate_resume import CandidateResume

UNSET_FILTER_VALUE = "__unset__"
UNSET_STATUS_KEY = "unset"
TOP_N_BUCKETS = 10
RECENT_APPLICATION_DAYS = 30

STATUS_LABELS = {
    "pending": "Pending",
    "on_hold": "On hold",
    "rejected": "Rejected",
    "selected": "Selected",
    UNSET_STATUS_KEY: "Not set",
}


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    status: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None


def clean_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    # Clients often send the grouped bucket key "unset" instead of the filter token "__unset__".
    if stripped == UNSET_FILTER_VALUE or stripped.lower() == UNSET_STATUS_KEY:
        return UNSET_FILTER_VALUE
    return stripped


def _is_blank_text_column(column):
    """
    True in SQL when the value is NULL, empty, or whitespace-only (after trim).
    Matches how filter buckets use nullif(btrim(col), '').
    """
    normalized = func.nullif(func.btrim(func.coalesce(column, "")), "")
    return normalized.is_(None)


def _apply_string_filter(query, column, value: Optional[str]):
    if value is None:
        return query
    if value == UNSET_FILTER_VALUE:
        return query.filter(_is_blank_text_column(column))
    return query.filter(func.lower(func.btrim(func.coalesce(column, ""))) == value.lower())


def apply_analytics_filters(query, filters: AnalyticsFilters):
    query = _apply_string_filter(query, CandidateStageComment.application_status, filters.status)
    query = _apply_string_filter(query, Application.applied_position, filters.position)
    query = _apply_string_filter(query, Application.applied_position_location, filters.location)
    return query


def status_coalesce_expr():
    return func.coalesce(
        func.nullif(func.btrim(CandidateStageComment.application_status), ""),
        UNSET_STATUS_KEY,
    )


def count_total_applications(db: Session, org_id: int, filters: AnalyticsFilters) -> int:
    q = (
        db.query(func.count(func.distinct(Application.id)))
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(CandidateProfile.organization_id == org_id)
    )
    return apply_analytics_filters(q, filters).scalar() or 0


def fetch_status_breakdown_rows(db: Session, org_id: int, filters: AnalyticsFilters):
    status_label_expr = status_coalesce_expr()
    q = (
        db.query(status_label_expr, func.count(func.distinct(Application.id)))
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(CandidateProfile.organization_id == org_id)
    )
    return (
        apply_analytics_filters(q, filters)
        .group_by(status_label_expr)
        .order_by(func.count(func.distinct(Application.id)).desc())
        .all()
    )


def grouped_count_rows(
    db: Session,
    org_id: int,
    group_column,
    filters: AnalyticsFilters,
    *,
    exclude_blank: bool = False,
    limit: int | None = None,
):
    query = (
        db.query(group_column, func.count(func.distinct(Application.id)))
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(CandidateProfile.organization_id == org_id)
    )
    if exclude_blank:
        query = query.filter(group_column.isnot(None), func.btrim(group_column) != "")
    query = apply_analytics_filters(query, filters)
    query = query.group_by(group_column).order_by(
        func.count(func.distinct(Application.id)).desc()
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def average_metric_by_position(
    db: Session,
    org_id: int,
    filters: AnalyticsFilters,
    value_expr,
    *,
    requires_value_filter,
):
    rows = (
        apply_analytics_filters(
            db.query(
                Application.applied_position,
                func.avg(value_expr),
                func.count(func.distinct(Application.id)),
            )
            .filter(
                CandidateProfile.organization_id == org_id,
                Application.applied_position.isnot(None),
                func.btrim(Application.applied_position) != "",
                requires_value_filter,
            )
            .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
            .outerjoin(
                CandidateStageComment,
                (CandidateStageComment.candidate_id == CandidateProfile.id)
                & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
            ),
            filters,
        )
        .group_by(Application.applied_position)
        .order_by(func.count(func.distinct(Application.id)).desc())
        .limit(TOP_N_BUCKETS)
        .all()
    )
    return [
        PositionAverageMetric(
            name=(str(row[0]) or "").strip() or "Unknown",
            average=round(float(row[1]), 2) if row[1] is not None else 0.0,
            sample_count=int(row[2]),
        )
        for row in rows
    ]


def build_filter_options(
    db: Session,
    organization_id: int,
    column,
    *,
    empty_label: str = "Not set",
    label_map: Optional[dict[str, str]] = None,
    include_empty_bucket: bool = True,
) -> List[AnalyticsFilterOption]:
    value_expr = func.nullif(func.btrim(column), "")
    rows = (
        db.query(value_expr, func.count(func.distinct(Application.id)))
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(CandidateProfile.organization_id == organization_id)
        .group_by(value_expr)
        .order_by(func.count(func.distinct(Application.id)).desc(), value_expr.asc())
        .all()
    )

    options: List[AnalyticsFilterOption] = []
    for raw_value, count in rows:
        if raw_value is None:
            if include_empty_bucket:
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


def count_candidates_with_resume(
    db: Session, org_id: int, filters: AnalyticsFilters
) -> int:
    q = (
        db.query(func.count(func.distinct(CandidateResume.id)))
        .join(CandidateProfile, CandidateProfile.id == CandidateResume.candidate_id)
        .join(Application, Application.candidate_id == CandidateProfile.id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(
            CandidateProfile.organization_id == org_id,
            CandidateResume.organization_id == org_id,
        )
    )
    return apply_analytics_filters(q, filters).scalar() or 0


def count_recent_applications(
    db: Session, org_id: int, filters: AnalyticsFilters, since: datetime
) -> int:
    q = (
        db.query(func.count(func.distinct(Application.id)))
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .outerjoin(
            CandidateStageComment,
            (CandidateStageComment.candidate_id == CandidateProfile.id)
            & (CandidateStageComment.organization_id == CandidateProfile.organization_id),
        )
        .filter(
            CandidateProfile.organization_id == org_id,
            Application.created_at >= since,
        )
    )
    return apply_analytics_filters(q, filters).scalar() or 0
