"""Shared result DTOs for all chatbot agents."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SQLGenerationResult(BaseModel):
    """LLM-generated SQL query."""
    sql: str
    explanation: str


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
    candidate_name: str


class CvInfoResult(BaseModel):
    """Full result from the CV info agent."""
    sql: str
    explanation: str
    rows: Optional[List[Dict[str, Any]]]
    total_found: int
    summary: str
    reply: str
