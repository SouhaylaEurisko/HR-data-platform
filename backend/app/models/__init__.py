"""
Models package — SQLAlchemy ORM models and Pydantic schemas.
"""

from .organization import Organization
from .lookup import LookupCategory, LookupOption
from .custom_field import CustomFieldDefinition
from .import_session import ImportSession
from .candidates import (
    CandidateApplicationStatusUpdate,
    CandidateListResponse,
    CandidateProfilePatchResponse,
    CandidateRead,
    CandidateUpdate,
    CandidateProfile,
    CandidateProfileListItem,
    CandidateProfileListResponse,
    RelatedApplicationSummary,
)
from .applications import Application
from .enums import ApplicationStatus, RelocationOpenness, TransportationAvailability

from .candidate_stage_comment import (
    CandidateApplicationStatusResponse,
    CandidateHrStageCommentCreate,
    CandidateHrStageCommentResponse,
    CandidateHrStageCommentsUpdateResponse,
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
    LoginRequest,
    LoginResponse,
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
    # New split candidate/application tables
    "CandidateProfile",
    "CandidateProfileListItem",
    "CandidateProfileListResponse",
    "Application",
    # Enums
    "ApplicationStatus",
    "RelocationOpenness",
    "TransportationAvailability",
    # Candidate models
    "CandidateApplicationStatusUpdate",
    "CandidateProfilePatchResponse",
    "CandidateUpdate",
    "CandidateHrStageCommentCreate",
    "CandidateHrStageCommentResponse",
    "CandidateHrStageCommentsUpdateResponse",
    "CandidateApplicationStatusResponse",
    "CandidateStageComment",
    "HrStageCommentEntryRead",
    "HrStageCommentsRead",
    "CandidateRead",
    "CandidateListResponse",
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
    "LoginRequest",
    "LoginResponse",
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
