"""
CandidateResume ORM — uploaded CV (BYTEA) and GPT-extracted resume_info (JSONB).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class CandidateResume(Base):
    __tablename__ = "candidate_resume"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    resume_info = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    candidate = relationship("CandidateProfile", back_populates="resume")
