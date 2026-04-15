"""Analytics filter and bucket DTOs (used by repository + schemas)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    status: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None


class AnalyticsFilterOption(BaseModel):
    """One selectable filter value exposed by analytics."""

    value: str = Field(description="Opaque value sent back to the analytics API")
    label: str = Field(description="Human-readable label shown in the UI")
    count: int = Field(ge=0, description="Candidates in this bucket for the full organization dataset")
