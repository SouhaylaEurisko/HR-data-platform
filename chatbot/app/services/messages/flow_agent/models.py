"""Models for Flow Agent."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FlowResult(BaseModel):
    """Unified result returned by the flow agent."""
    intent: str                             # classified intent
    reply: str                              # text reply for the user
    summary: Optional[str] = None           # explanatory paragraph (filter/agg)
    rows: Optional[List[Dict[str, Any]]] = None     # candidate rows (filter)
    stats: Optional[List[Dict[str, Any]]] = None    # aggregation stats
    total_found: Optional[int] = None
    sql: Optional[str] = None               # generated SQL (for debugging)
    explanation: Optional[str] = None       # SQL explanation
