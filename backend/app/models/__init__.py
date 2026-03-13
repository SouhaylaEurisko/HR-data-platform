"""
Models package — SQLAlchemy ORM models and Pydantic schemas.
"""

from .candidate import (
    DataSource,
    DataSourceRead,
    Candidate,
    CandidateBase,
    CandidateCreate,
    CandidateRead,
    CandidateListResponse,
)
from .chat import (
    QuestionClassification,
    ChatSearchFilters,
    AggregationRequest,
    AggregationResult,
    ChatRequest,
    ChatResponse,
)
from .user import (
    User,
    UserBase,
    UserCreate,
    UserRead,
    UserLogin,
)

__all__ = [
    # DataSource models
    "DataSource",
    "DataSourceRead",
    # Candidate models
    "Candidate",
    "CandidateBase",
    "CandidateCreate",
    "CandidateRead",
    "CandidateListResponse",
    # Chat models
    "QuestionClassification",
    "ChatSearchFilters",
    "AggregationRequest",
    "AggregationResult",
    "ChatRequest",
    "ChatResponse",
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserLogin",
]
