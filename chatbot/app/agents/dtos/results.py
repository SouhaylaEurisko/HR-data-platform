"""Shared result DTOs for all chatbot agents."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SQLGenerationResult(BaseModel):
    """LLM-generated SQL query."""
    sql: str
    explanation: str


class FilterSummaryResult(BaseModel):
    """LLM-generated natural-language summary for filter results."""
    summary: str
    reply: str


class AggregationSummaryResult(BaseModel):
    """LLM-generated natural-language summary for aggregation results."""
    summary: str
    reply: str


class FilterAggregationSQLResult(BaseModel):
    """LLM-generated SQL pair for combined filter + aggregation queries."""
    filter_sql: str
    aggregation_sql: str
    explanation: str


class FilterAggSummaryResult(BaseModel):
    """LLM-generated summary for combined filter+aggregation results."""
    summary: str
    reply: str


class CvInfoSummaryResult(BaseModel):
    """LLM-generated summary for CV info results."""
    summary: str
    reply: str


class FilterAgentResult(BaseModel):
    """Full result from the filter agent."""
    sql: str
    explanation: str
    rows: List[Dict[str, Any]]
    total_found: int
    summary: str
    reply: str


class AggregationAgentResult(BaseModel):
    """Full result from the aggregation agent."""
    sql: str
    explanation: str
    stats: List[Dict[str, Any]]
    summary: str
    reply: str


class FilterAggregationResult(BaseModel):
    """Full result combining filter rows AND aggregation stats."""
    filter_sql: str
    aggregation_sql: str
    explanation: str
    rows: List[Dict[str, Any]]
    stats: List[Dict[str, Any]]
    total_found: int
    summary: str
    reply: str


class ChitChatResult(BaseModel):
    reply: str


class IntentClassificationResult(BaseModel):
    """LLM classification output."""
    intent: str
    confidence: str
    reasoning: str


class FlowResult(BaseModel):
    """Unified result returned by the flow agent."""
    intent: str
    reply: str
    summary: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    stats: Optional[List[Dict[str, Any]]] = None
    total_found: Optional[int] = None
    sql: Optional[str] = None
    explanation: Optional[str] = None


class TitleResult(BaseModel):
    title: str


class CvInfoExtraction(BaseModel):
    """Extracted inputs for a CV info query."""
    candidate_name: str
    question_type: str = "profile"


class CvInfoResult(BaseModel):
    """Full result from the CV info agent."""
    sql: str
    explanation: str
    rows: Optional[List[Dict[str, Any]]]
    total_found: int
    summary: str
    reply: str


class HrFeedbackExtraction(BaseModel):
    """Extracted candidate + stage from an HR feedback query."""
    candidate_name: str = ""
    stage: Optional[str] = None


class ComparisonExtraction(BaseModel):
    """Extracted inputs for a candidate comparison query.

    ``scope`` is typed as ``str`` (rather than a ``Literal``) so that an
    unexpected LLM value doesn't cause a hard validation failure — the
    candidate-comparison agent normalises unknown scopes to ``"named_only"``.
    """
    candidate_names: List[str] = Field(default_factory=list)
    position_filter: str = ""
    scope: str = "named_only"
    comparison_criteria: str = ""
    use_agent_default_criteria: bool = False

    @field_validator("candidate_names", mode="before")
    @classmethod
    def _coerce_candidate_names(cls, value: Any) -> Any:
        """Tolerate ``null`` or a single string from the LLM."""
        if value is None:
            return []
        if isinstance(value, str):
            trimmed = value.strip()
            return [trimmed] if trimmed else []
        return value


class ComparisonDecision(BaseModel):
    """LLM-produced recommendation for a candidate comparison."""
    reply: str
    summary: Optional[str] = None
    recommended_full_name: Optional[str] = None
