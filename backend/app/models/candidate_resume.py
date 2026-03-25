"""
CandidateResume model — stores uploaded CV/resume files (BYTEA) and
GPT-extracted structured data (resume_info JSONB) per candidate.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, LargeBinary, String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class CandidateResume(Base):
    __tablename__ = "candidate_resume"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidate.id", ondelete="CASCADE"),
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
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    candidate = relationship("Candidate", back_populates="resume")


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────


class WorkExperienceRead(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class EducationRead(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ResumeInfoRead(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    languages: List[str] = []
    work_experience: List[WorkExperienceRead] = []
    education: List[EducationRead] = []
    certifications: List[str] = []


class CandidateResumeRead(BaseModel):
    id: int
    candidate_id: int
    organization_id: int
    filename: str
    content_type: str
    resume_info: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
