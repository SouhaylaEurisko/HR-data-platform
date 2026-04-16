"""Assemble AnalyticsOverviewResponse from repository query results."""

from typing import List

from ..dtos.analytics import AnalyticsFilters
from ..schemas.analytics import (
    AnalyticsAppliedFilters,
    AnalyticsFilterOptions,
    AnalyticsOverviewResponse,
    NamedCount,
    PositionAverageMetric,
)


def build_analytics_overview_response(
    *,
    total: int,
    by_status: List[NamedCount],
    top_positions: List[NamedCount],
    top_locations: List[NamedCount],
    avg_expected_salary_by_position: List[PositionAverageMetric],
    avg_years_experience_by_position: List[PositionAverageMetric],
    with_resume: int,
    pct_resume: float,
    recent: int,
    filter_options: AnalyticsFilterOptions,
    filters: AnalyticsFilters,
) -> AnalyticsOverviewResponse:
    return AnalyticsOverviewResponse(
        total_candidates=int(total),
        by_application_status=by_status,
        top_applied_positions=top_positions,
        top_locations=top_locations,
        avg_expected_salary_by_position=avg_expected_salary_by_position,
        avg_years_experience_by_position=avg_years_experience_by_position,
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
