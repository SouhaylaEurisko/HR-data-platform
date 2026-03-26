"""Pydantic schemas for org-scoped analytics API responses."""

from typing import List

from pydantic import BaseModel, Field


class NamedCount(BaseModel):
    """Single bucket in a breakdown (e.g. status or position)."""

    name: str
    count: int = Field(ge=0)


class AnalyticsOverviewResponse(BaseModel):
    """KPI snapshot for one organization."""

    total_candidates: int = Field(ge=0)
    by_application_status: List[NamedCount]
    top_applied_positions: List[NamedCount]
    top_locations: List[NamedCount]
    candidates_with_resume: int = Field(ge=0)
    resume_coverage_percent: float = Field(ge=0, le=100)
    recent_applications_30d: int = Field(ge=0, description="created_at in last 30 days")
