"""
Models package — SQLAlchemy ORM models and Pydantic schemas.
"""

from .organization import Organization
from .lookup import LookupCategory, LookupOption
from .custom_field import CustomFieldDefinition
from .import_session import ImportSession
from .candidate import (
    Candidate,
    CandidateBase,
    CandidateCreate,
    CandidateRead,
    CandidateListResponse,
    LookupOptionLabel,
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
    # Candidate models
    "Candidate",
    "CandidateBase",
    "CandidateCreate",
    "CandidateRead",
    "CandidateListResponse",
    "LookupOptionLabel",
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
