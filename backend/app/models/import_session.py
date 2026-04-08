"""
ImportSession -- tracks each Excel file upload as a discrete event.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Any, Dict, List

from pydantic import BaseModel

from ..config.database import Base


class ImportSession(Base):
    __tablename__ = "import_session"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("user_account.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    import_sheet = Column(String(255), nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)
    total_rows = Column(Integer, default=0, nullable=False)
    imported_rows = Column(Integer, default=0, nullable=False)
    skipped_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)
    summary = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="import_sessions")
    uploaded_by = relationship("UserAccount")
    candidate_profiles = relationship("CandidateProfile", back_populates="import_session")



# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class ConfirmImportRequest(BaseModel):
    session_id: int
    confirmed_mappings: Dict[str, str]
    new_custom_fields: List[Dict[str, Any]] = []
    skip_columns: List[str] = []
    sheet_names: List[str]
    org_id: int


class DuplicateCheckRequest(BaseModel):
    filename: str
    sheet_names: List[str]
    org_id: int = 1