"""Models for CV Info Agent."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CvInfoExtraction(BaseModel):
    """LLM-extracted candidate name from the user query."""
    candidate_name: str


class CvInfoResult(BaseModel):
    """Full result from the CV info agent."""
    sql: str
    explanation: str
    rows: Optional[List[Dict[str, Any]]] = None
    total_found: int
    summary: str
    reply: str
