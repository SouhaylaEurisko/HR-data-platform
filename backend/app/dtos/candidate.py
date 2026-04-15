"""Candidate list / filter parameters for repository queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
