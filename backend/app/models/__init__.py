"""
Models package — SQLAlchemy ORM models and Pydantic schemas.
"""

from .organization import Organization
from .lookup import LookupCategory, LookupOption
from .custom_field import CustomFieldDefinition
from .import_session import ImportSession
from .enums import ApplicationStatus, RelocationOpenness
from .candidate import (
    Candidate,
    CandidateApplicationStatusUpdate,
    CandidateBase,
    CandidateCreate,
    CandidateHrCommentUpdate,
    CandidateRead,
    CandidateListResponse,
    HrStageCommentsRead,
    LookupOptionLabel,
    RelatedApplicationSummary,
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
    UserAccount,
    UserBase,
    UserCreate,
    UserRead,
    UserLogin,
)
from .conversation import (
    Conversation,
    Message,
    ConversationRead,
    ConversationCreate,
    ConversationWithMessages,
    MessageRead,
    MessageCreate,
)

__all__ = [
    # Organization
    "Organization",
    # Lookup
    "LookupCategory",
    "LookupOption",
    # Custom fields
    "CustomFieldDefinition",
    # Import session
    "ImportSession",
    # Enums
    "ApplicationStatus",
    "RelocationOpenness",
    # Candidate models
    "Candidate",
    "CandidateApplicationStatusUpdate",
    "CandidateBase",
    "CandidateCreate",
    "CandidateHrCommentUpdate",
    "HrStageCommentsRead",
    "CandidateRead",
    "CandidateListResponse",
    "LookupOptionLabel",
    "RelatedApplicationSummary",
    # Chat models
    "QuestionClassification",
    "ChatSearchFilters",
    "AggregationRequest",
    "AggregationResult",
    "ChatRequest",
    "ChatResponse",
    # User models
    "UserAccount",
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserLogin",
    # Conversation and Message
    "Conversation",
    "Message",
    "ConversationRead",
    "ConversationCreate",
    "ConversationWithMessages",
    "MessageRead",
    "MessageCreate",
]
