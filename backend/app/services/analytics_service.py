"""
Org-scoped analytics — aggregates applications (+ resume) data.
SQL lives in repository.analytics_repository.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Protocol

from sqlalchemy import func, or_

from ..dtos.analytics import AnalyticsFilters
from ..models.applications import Application
from ..schemas.analytics import (
    AnalyticsAppliedFilters,
    AnalyticsFilterOptions,
    AnalyticsOverviewResponse,
    NamedCount,
)
from ..constants import Analytics, STATUS_LABELS
from ..repository.analytics_repository import AnalyticsRepositoryProtocol

UNSET_STATUS_KEY = Analytics.UNSET_STATUS_KEY
TOP_N_BUCKETS = Analytics.TOP_N_BUCKETS
RECENT_APPLICATION_DAYS = Analytics.RECENT_APPLICATION_DAYS
_STATUS_LABELS = STATUS_LABELS


def _named_counts(rows: list[tuple[str | None, int]], *, empty_label: str = "Unknown") -> List[NamedCount]:
    out: List[NamedCount] = []
    for name, cnt in rows:
        label = (name or "").strip() or empty_label
        out.append(NamedCount(name=label, count=int(cnt)))
    return out


def _status_label(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        normalized = UNSET_STATUS_KEY
    return _STATUS_LABELS.get(normalized, normalized.replace("_", " ").title())


class AnalyticsServiceProtocol(Protocol):
    def get_analytics_overview(
        self,
        organization_id: int,
        *,
        status: Optional[str] = None,
        position: Optional[str] = None,
        location: Optional[str] = None,
    ) -> AnalyticsOverviewResponse: ...


class AnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepositoryProtocol) -> None:
        self._analytics_repo = analytics_repo

    def get_analytics_overview(
        self,
        organization_id: int,
        *,
        status: Optional[str] = None,
        position: Optional[str] = None,
        location: Optional[str] = None,
    ) -> AnalyticsOverviewResponse:
        org = organization_id
        now = datetime.now(timezone.utc)
        filters = AnalyticsFilters(
            status=self._analytics_repo.clean_filter(status),
            position=self._analytics_repo.clean_filter(position),
            location=self._analytics_repo.clean_filter(location),
        )

        total = self._analytics_repo.count_total_applications(org, filters)

        status_rows = self._analytics_repo.fetch_status_breakdown_rows(org, filters)
        by_status = [NamedCount(name=_status_label(r[0]), count=int(r[1])) for r in status_rows]

        pos_rows = self._analytics_repo.grouped_count_rows(
            org,
            Application.applied_position,
            filters,
            exclude_blank=True,
            limit=TOP_N_BUCKETS,
        )
        top_positions = _named_counts(pos_rows, empty_label="Unknown")

        loc_rows = self._analytics_repo.grouped_count_rows(
            org,
            Application.applied_position_location,
            filters,
            exclude_blank=True,
            limit=TOP_N_BUCKETS,
        )
        top_locations = _named_counts(loc_rows, empty_label="Unknown")

        salary_expr = func.coalesce(Application.expected_salary_remote, Application.expected_salary_onsite)
        avg_salary_by_pos = self._analytics_repo.average_metric_by_position(
            org,
            filters,
            salary_expr,
            requires_value_filter=or_(
                Application.expected_salary_remote.isnot(None),
                Application.expected_salary_onsite.isnot(None),
            ),
        )

        avg_yoe_by_pos = self._analytics_repo.average_metric_by_position(
            org,
            filters,
            Application.years_of_experience,
            requires_value_filter=Application.years_of_experience.isnot(None),
        )

        with_resume = self._analytics_repo.count_candidates_with_resume(org, filters)
        pct_resume = round(100.0 * with_resume / total, 1) if total else 0.0

        since = now - timedelta(days=RECENT_APPLICATION_DAYS)
        recent = self._analytics_repo.count_recent_applications(org, filters, since)

        status_label_expr = self._analytics_repo.status_coalesce_expr()
        filter_options = AnalyticsFilterOptions(
            statuses=self._analytics_repo.build_filter_options(
                org,
                status_label_expr,
                empty_label="Not set",
                label_map=_STATUS_LABELS,
            ),
            positions=self._analytics_repo.build_filter_options(
                org,
                Application.applied_position,
                include_empty_bucket=False,
            ),
            locations=self._analytics_repo.build_filter_options(
                org,
                Application.applied_position_location,
                include_empty_bucket=False,
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

