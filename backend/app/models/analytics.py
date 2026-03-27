"""Pydantic schemas for org-scoped analytics API responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class NamedCount(BaseModel):
    """Single bucket in a breakdown (e.g. status or position)."""

    name: str
    count: int = Field(ge=0)


class PositionAverageMetric(BaseModel):
    """Average of a numeric field grouped by applied_position."""

    name: str = Field(description="applied_position label")
    average: float
    sample_count: int = Field(ge=0, description="Candidates included in the average")


class AnalyticsFilterOption(BaseModel):
    """One selectable filter value exposed by analytics."""

    value: str = Field(description="Opaque value sent back to the analytics API")
    label: str = Field(description="Human-readable label shown in the UI")
    count: int = Field(ge=0, description="Candidates in this bucket for the full organization dataset")


class AnalyticsFilterOptions(BaseModel):
    """Available filter options for the analytics page."""

    statuses: List[AnalyticsFilterOption]
    positions: List[AnalyticsFilterOption]
    locations: List[AnalyticsFilterOption]


class AnalyticsAppliedFilters(BaseModel):
    """Filters currently applied to the analytics payload."""

    status: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None


class AnalyticsOverviewResponse(BaseModel):
    """KPI snapshot for one organization."""

    total_candidates: int = Field(ge=0)
    by_application_status: List[NamedCount]
    top_applied_positions: List[NamedCount]
    top_locations: List[NamedCount]
    avg_expected_salary_by_position: List[PositionAverageMetric]
    avg_years_experience_by_position: List[PositionAverageMetric]
    candidates_with_resume: int = Field(ge=0)
    resume_coverage_percent: float = Field(ge=0, le=100)
    recent_applications_30d: int = Field(ge=0, description="created_at in last 30 days")
    filter_options: AnalyticsFilterOptions
    applied_filters: AnalyticsAppliedFilters
