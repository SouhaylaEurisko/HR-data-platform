"""Structured resume payload produced by the resume parser agent (internal)."""

from typing import List, Optional

from pydantic import BaseModel


class WorkExperience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ResumeInfo(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    languages: List[str] = []
    work_experience: List[WorkExperience] = []
    education: List[Education] = []
    certifications: List[str] = []
