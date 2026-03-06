from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Candidate
from ..schemas import CandidateRead
from .prompts import AGGREGATION_DETECTION_PROMPT, FILTER_EXTRACTION_PROMPT

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatSearchFilters(BaseModel):
    position: Optional[str] = None
    min_expected_salary: Optional[float] = Field(default=None, ge=0)
    max_expected_salary: Optional[float] = Field(default=None, ge=0)
    min_years_experience: Optional[float] = Field(default=None, ge=0)
    max_years_experience: Optional[float] = Field(default=None, ge=0)
    nationality: Optional[str] = None
    current_address: Optional[str] = None


class AggregationRequest(BaseModel):
    """Detects if the question is asking for aggregations/statistics"""
    is_aggregation: bool = False
    aggregation_type: Optional[Literal["count", "average", "sum", "min", "max", "all"]] = None
    aggregation_field: Optional[Literal["salary", "experience", "total", "all"]] = None


class AggregationResult(BaseModel):
    """Aggregation statistics"""
    total_count: Optional[int] = None
    avg_salary: Optional[float] = None
    avg_experience: Optional[float] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    filters: ChatSearchFilters
    total_matches: int
    top_candidates: list[CandidateRead]
    aggregations: Optional[AggregationResult] = None


def _build_openai_client():
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key), settings.openai_model


def _detect_aggregation_request(question: str) -> AggregationRequest:
    """Detect if the question is asking for aggregations/statistics"""
    client, model = _build_openai_client()
    
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": AGGREGATION_DETECTION_PROMPT},
            {"role": "user", "content": question},
        ],
        response_format={"type": "json_object"},
    )
    
    raw_content = completion.choices[0].message.content
    try:
        import json
        data = json.loads(raw_content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse aggregation detection JSON: {exc}",
        ) from exc
    
    return AggregationRequest.model_validate(data)


def _ask_model_for_filters(question: str) -> ChatSearchFilters:
    client, model = _build_openai_client()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": FILTER_EXTRACTION_PROMPT,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        response_format={"type": "json_object"},
    )

    raw_content = completion.choices[0].message.content
    try:
        import json

        data = json.loads(raw_content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse model JSON: {exc}",
        ) from exc

    return ChatSearchFilters.model_validate(data)


def _build_base_query(filters: ChatSearchFilters):
    """Build the base query with filters applied"""
    query = select(Candidate)

    if filters.position:
        query = query.where(Candidate.position.ilike(f"%{filters.position}%"))
    if filters.nationality:
        query = query.where(Candidate.nationality.ilike(f"%{filters.nationality}%"))
    if filters.current_address:
        query = query.where(
            Candidate.current_address.ilike(f"%{filters.current_address}%")
        )
    if filters.min_expected_salary is not None:
        query = query.where(Candidate.expected_salary >= filters.min_expected_salary)
    if filters.max_expected_salary is not None:
        query = query.where(Candidate.expected_salary <= filters.max_expected_salary)
    if filters.min_years_experience is not None:
        query = query.where(
            Candidate.years_experience >= filters.min_years_experience
        )
    if filters.max_years_experience is not None:
        query = query.where(
            Candidate.years_experience <= filters.max_years_experience
        )

    return query


def _calculate_aggregations(
    db: Session,
    filters: ChatSearchFilters,
    agg_request: AggregationRequest,
) -> AggregationResult:
    """Calculate aggregation statistics based on filters"""
    # Build base query with all filters
    base_query = _build_base_query(filters)
    
    # Always calculate total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_count = db.scalar(count_query) or 0
    
    result = AggregationResult(total_count=total_count if total_count > 0 else None)
    
    # If no candidates, return early
    if total_count == 0:
        return result
    
    # Calculate salary aggregations if requested
    if agg_request.aggregation_field in ("salary", "all") or (
        agg_request.aggregation_type == "average" and agg_request.aggregation_field is None
    ):
        # Build query with salary filters and non-null check
        salary_query = _build_base_query(filters)
        salary_query = salary_query.where(Candidate.expected_salary.isnot(None))
        
        # Get all matching candidates with salaries
        candidates_with_salary = db.execute(salary_query).scalars().all()
        salaries = [c.expected_salary for c in candidates_with_salary if c.expected_salary is not None]
        
        if salaries:
            result.avg_salary = round(sum(salaries) / len(salaries), 2)
            result.min_salary = float(min(salaries))
            result.max_salary = float(max(salaries))
    
    # Calculate experience aggregations if requested
    if agg_request.aggregation_field in ("experience", "all") or (
        agg_request.aggregation_type == "average" and agg_request.aggregation_field is None
    ):
        # Build query with experience filters and non-null check
        exp_query = _build_base_query(filters)
        exp_query = exp_query.where(Candidate.years_experience.isnot(None))
        
        # Get all matching candidates with experience
        candidates_with_exp = db.execute(exp_query).scalars().all()
        experiences = [c.years_experience for c in candidates_with_exp if c.years_experience is not None]
        
        if experiences:
            result.avg_experience = round(sum(experiences) / len(experiences), 2)
            result.min_experience = float(min(experiences))
            result.max_experience = float(max(experiences))
    
    return result


def _query_candidates_with_filters(
    db: Session,
    filters: ChatSearchFilters,
    limit: int = 10,
) -> tuple[list[Candidate], int]:
    base_query = _build_base_query(filters)
    
    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

    query = base_query.order_by(Candidate.created_at.desc()).limit(limit)
    results = db.execute(query).scalars().all()

    return results, total


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Turn a natural language HR question into candidate filters and return matching candidates.
    Supports both regular searches and aggregation queries (count, average, etc.).
    """
    # 1) Detect if this is an aggregation request
    agg_request = _detect_aggregation_request(payload.message)
    
    # 2) Ask the LLM for structured filters (even for aggregations, we need filters)
    filters = _ask_model_for_filters(payload.message)

    # 3) Handle aggregation queries
    if agg_request.is_aggregation:
        aggregations = _calculate_aggregations(db=db, filters=filters, agg_request=agg_request)
        
        # Build aggregation reply
        reply_parts = []
        
        if agg_request.aggregation_type == "count" or agg_request.aggregation_type is None:
            if aggregations.total_count is not None:
                reply_parts.append(f"There are {aggregations.total_count} candidate{'s' if aggregations.total_count != 1 else ''} matching your criteria.")
        
        if agg_request.aggregation_type in ("average", "all") or (
            agg_request.aggregation_type is None and agg_request.aggregation_field == "all"
        ):
            if aggregations.avg_salary is not None:
                reply_parts.append(f"The average expected salary is ${aggregations.avg_salary:,.2f} USD.")
            if aggregations.avg_experience is not None:
                reply_parts.append(f"The average years of experience is {aggregations.avg_experience} years.")
        
        if agg_request.aggregation_type in ("min", "all"):
            if aggregations.min_salary is not None:
                reply_parts.append(f"The minimum expected salary is ${aggregations.min_salary:,.2f} USD.")
            if aggregations.min_experience is not None:
                reply_parts.append(f"The minimum years of experience is {aggregations.min_experience} years.")
        
        if agg_request.aggregation_type in ("max", "all"):
            if aggregations.max_salary is not None:
                reply_parts.append(f"The maximum expected salary is ${aggregations.max_salary:,.2f} USD.")
            if aggregations.max_experience is not None:
                reply_parts.append(f"The maximum years of experience is {aggregations.max_experience} years.")
        
        if not reply_parts:
            reply_parts.append("No candidates found matching your criteria.")
        
        reply_text = " ".join(reply_parts)
        
        # For aggregations, we might still want to show some candidates
        candidates, total = _query_candidates_with_filters(db=db, filters=filters, limit=5)
        
        return ChatResponse(
            reply=reply_text,
            filters=filters,
            total_matches=aggregations.total_count or total,
            top_candidates=[CandidateRead.model_validate(c) for c in candidates],
            aggregations=aggregations,
        )
    
    # 4) Handle regular search queries
    candidates, total = _query_candidates_with_filters(db=db, filters=filters)

    # 5) Build a friendly reply
    if not candidates:
        reply_text = "No candidates matched your search criteria."
    else:
        reply_text = f"I found {total} candidate{'s' if total != 1 else ''} matching your criteria."

    return ChatResponse(
        reply=reply_text,
        filters=filters,
        total_matches=total,
        top_candidates=[CandidateRead.model_validate(c) for c in candidates],
        aggregations=None,
    )


