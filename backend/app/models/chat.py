"""
Chat models — Pydantic request/response schemas for the AI chat endpoint.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .candidates import CandidateRead


class QuestionClassification(BaseModel):
    """Classifies the type of user question."""
    is_candidate_related: bool = False
    question_type: Optional[
        Literal["candidate_search", "aggregation", "greeting", "conversational", "off_topic"]
    ] = None
    requires_data: bool = False


class ChatSearchFilters(BaseModel):
    """
    Filters extracted from chat; richer than the Candidates page API.
    Used only by the chat pipeline when calling list_candidates internally.
    """
    position: Optional[str] = None
    name: Optional[str] = Field(default=None, description="Candidate full name substring")
    email: Optional[str] = Field(default=None, description="Email substring")
    nationality: Optional[str] = None
    min_years_experience: Optional[float] = Field(default=None, ge=0)
    max_years_experience: Optional[float] = Field(default=None, ge=0)
    min_expected_salary_remote: Optional[float] = Field(default=None, ge=0)
    max_expected_salary_remote: Optional[float] = Field(default=None, ge=0)
    min_expected_salary_onsite: Optional[float] = Field(default=None, ge=0)
    max_expected_salary_onsite: Optional[float] = Field(default=None, ge=0)


class AggregationRequest(BaseModel):
    """Detects whether the question asks for aggregations/statistics."""
    is_aggregation: bool = False
    aggregation_type: Optional[Literal["count", "average", "sum", "min", "max", "all"]] = None
    aggregation_field: Optional[Literal["salary", "experience", "total", "all"]] = None


class AggregationResult(BaseModel):
    """Aggregation statistics returned to the client."""
    total_count: Optional[int] = None
    avg_salary: Optional[float] = None
    avg_experience: Optional[float] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str


class ChatResponse(BaseModel):
    """Full response returned by the chat endpoint."""
    reply: str
    filters: ChatSearchFilters
    total_matches: int
    top_candidates: list[CandidateRead]
    aggregations: Optional[AggregationResult] = None
