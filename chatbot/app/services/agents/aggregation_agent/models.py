"""Models for Aggregation Agent."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AggregationAgentResult(BaseModel):
    """Full result from the aggregation agent."""
    sql: str
    explanation: str
    stats: List[Dict[str, Any]]  # raw aggregation rows
    summary: str   # human-readable paragraph
    reply: str     # final reply text
