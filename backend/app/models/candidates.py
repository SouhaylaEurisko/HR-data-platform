"""
New candidates table (split from the legacy flat candidate table).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from ..config.database import Base
from .candidate_stage_comment import HrStageCommentsRead
from .enums import ApplicationStatus, RelocationOpenness, TransportationAvailability


class CandidateProfile(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    import_session_id = Column(Integer, ForeignKey("import_session.id"), nullable=True, index=True)
    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(320), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    organization = relationship("Organization", back_populates="candidates")
    import_session = relationship("ImportSession", back_populates="candidate_profiles")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    resume = relationship(
        "CandidateResume",
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CandidateProfileListItem(BaseModel):
    id: int
    organization_id: int
    import_session_id: int | None = None
    full_name: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    created_at: datetime
    applied_position: str | None = None
    is_open_for_relocation: RelocationOpenness | None = None
    application_status: ApplicationStatus | None = None
    hr_stage_comments: HrStageCommentsRead = Field(default_factory=HrStageCommentsRead)

    class Config:
        from_attributes = True


class CandidateProfileListResponse(BaseModel):
    items: list[CandidateProfileListItem]
    total: int
    page: int
    page_size: int


class RelatedApplicationSummary(BaseModel):
    """Another application (row) for the same email within the org."""

    id: int
    applied_position: Optional[str] = None
    applied_at: Optional[datetime] = None
    created_at: datetime


class CandidateApplicationStatusUpdate(BaseModel):
    """PATCH body: application status only (separate from HR comments save)."""

    application_status: ApplicationStatus


class CandidateUpdate(BaseModel):
    """PATCH body: only fields present in the request are updated (partial update)."""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    current_address: Optional[str] = None
    residency_type_id: Optional[int] = None
    marital_status_id: Optional[int] = None
    number_of_dependents: Optional[int] = None
    religion_sect: Optional[str] = None
    passport_validity_status_id: Optional[int] = None
    has_transportation: Optional[TransportationAvailability] = None
    applied_position: Optional[str] = None
    applied_position_location: Optional[str] = None
    is_open_for_relocation: Optional[RelocationOpenness] = None
    years_of_experience: Optional[Decimal] = None
    is_employed: Optional[bool] = None
    current_salary: Optional[Decimal] = None
    expected_salary_remote: Optional[Decimal] = None
    expected_salary_onsite: Optional[Decimal] = None
    notice_period: Optional[str] = None
    is_overtime_flexible: Optional[bool] = None
    is_contract_flexible: Optional[bool] = None
    workplace_type_id: Optional[int] = None
    employment_type_id: Optional[int] = None
    tech_stack: Optional[List[str]] = None
    education_level_id: Optional[int] = None
    education_completion_status_id: Optional[int] = None


class CandidateBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    current_address: Optional[str] = None
    residency_type_id: Optional[int] = None
    marital_status_id: Optional[int] = None
    number_of_dependents: Optional[int] = None
    religion_sect: Optional[str] = None
    passport_validity_status_id: Optional[int] = None
    has_transportation: Optional[TransportationAvailability] = None

    applied_position: Optional[str] = None
    applied_position_location: Optional[str] = None
    is_open_for_relocation: Optional[RelocationOpenness] = None
    years_of_experience: Optional[Decimal] = Field(default=None, ge=0)
    is_employed: Optional[bool] = None
    current_salary: Optional[Decimal] = Field(default=None, ge=0)
    expected_salary_remote: Optional[Decimal] = Field(default=None, ge=0)
    expected_salary_onsite: Optional[Decimal] = Field(default=None, ge=0)
    notice_period: Optional[str] = None
    is_overtime_flexible: Optional[bool] = None
    is_contract_flexible: Optional[bool] = None
    workplace_type_id: Optional[int] = None
    employment_type_id: Optional[int] = None
    tech_stack: Optional[List[str]] = None
    education_level_id: Optional[int] = None
    education_completion_status_id: Optional[int] = None

    custom_fields: Optional[Dict[str, Any]] = None


class CandidateRead(CandidateBase):
    id: int
    organization_id: int
    import_session_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    raw_import_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    hr_stage_comments: HrStageCommentsRead = Field(default_factory=HrStageCommentsRead)
    application_status: Optional[ApplicationStatus] = None

    # Import source (from import_session when loaded)
    import_filename: Optional[str] = None
    import_sheet: Optional[str] = None

    # Resolved lookup labels (populated by service layer)
    residency_type_label: Optional[str] = None
    marital_status_label: Optional[str] = None
    passport_validity_status_label: Optional[str] = None
    workplace_type_label: Optional[str] = None
    employment_type_label: Optional[str] = None
    education_level_label: Optional[str] = None
    education_completion_status_label: Optional[str] = None

    # Same-email applications (detail view only; list responses omit / use defaults)
    application_index: Optional[int] = None
    application_total: Optional[int] = None
    related_applications: List[RelatedApplicationSummary] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int
