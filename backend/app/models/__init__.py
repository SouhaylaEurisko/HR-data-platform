"""
Models package — SQLAlchemy ORM models and Pydantic schemas.
"""

from .organization import Organization
from .lookup import LookupCategory, LookupOption
from .custom_field import CustomFieldDefinition
from .import_session import ImportSession
from .enums import ApplicationStatus, RelocationOpenness, TransportationAvailability
from .candidate import (
    Candidate,
    CandidateApplicationStatusUpdate,
    CandidateBase,
    CandidateCreate,
    CandidateRead,
    CandidateListResponse,
    LookupOptionLabel,
    RelatedApplicationSummary,
)
from .candidate_stage_comment import (
    CandidateHrStageCommentCreate,
    CandidateStageComment,
    HrStageCommentEntryRead,
    HrStageCommentsRead,
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
from .candidate_resume import (
    CandidateResume,
    CandidateResumeRead,
    ResumeInfoRead,
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
    "TransportationAvailability",
    # Candidate models
    "Candidate",
    "CandidateApplicationStatusUpdate",
    "CandidateBase",
    "CandidateCreate",
    "CandidateHrStageCommentCreate",
    "CandidateStageComment",
    "HrStageCommentEntryRead",
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
    # Candidate resume
    "CandidateResume",
    "CandidateResumeRead",
    "ResumeInfoRead",
    # Conversation and Message
    "Conversation",
    "Message",
    "ConversationRead",
    "ConversationCreate",
    "ConversationWithMessages",
    "MessageRead",
    "MessageCreate",
]
