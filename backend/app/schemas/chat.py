"""Chat HTTP request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from ..dtos.chat import AggregationResult, ChatSearchFilters
from .candidate import CandidateRead


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str


class ChatResponse(BaseModel):
    """Full response returned by the chat endpoint."""

    reply: str
    filters: ChatSearchFilters
    total_matches: int
    top_candidates: list[CandidateRead]
    aggregations: AggregationResult | None = None
