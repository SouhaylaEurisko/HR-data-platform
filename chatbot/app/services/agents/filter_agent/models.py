"""Models for Filter Agent."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SQLGenerationResult(BaseModel):
    """LLM-generated SQL query."""
    sql: str
    explanation: str  # what the query does


class FilterAgentResult(BaseModel):
    """Full result from the filter agent."""
    sql: str
    explanation: str
    rows: List[Dict[str, Any]]
    total_found: int
    summary: str  # human-readable paragraph about the results
    reply: str    # final reply text shown to user
