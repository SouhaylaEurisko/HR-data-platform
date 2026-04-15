"""Resume API read schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
