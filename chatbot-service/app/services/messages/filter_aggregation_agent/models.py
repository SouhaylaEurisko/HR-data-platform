"""Models for Filter + Aggregation Agent."""
from typing import Any, Dict, List
from pydantic import BaseModel


class FilterAggregationResult(BaseModel):
    """Full result combining filter rows AND aggregation stats."""
    filter_sql: str
    aggregation_sql: str
    explanation: str
    rows: List[Dict[str, Any]]      # filtered candidate rows
    stats: List[Dict[str, Any]]     # aggregation stats
    total_found: int
    summary: str
    reply: str
