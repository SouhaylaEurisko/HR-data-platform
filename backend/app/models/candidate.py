"""
Candidate models — SQLAlchemy ORM table + Pydantic request/response schemas.
Rich field set drawn from DATABASE_DESIGN.md.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer,
    Numeric, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


# ──────────────────────────────────────────────
# SQLAlchemy ORM model
# ──────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidate"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    import_session_id = Column(Integer, ForeignKey("import_session.id"), nullable=True, index=True)
    import_sheet = Column(String(255), nullable=True)

    # -- Meta --
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # -- Personal --
    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(320), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(100), nullable=True, index=True)
    current_address = Column(Text, nullable=True)
    residency_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    marital_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    number_of_dependents = Column(SmallInteger, nullable=True)
    religion_sect = Column(String(100), nullable=True)
    passport_validity_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    has_transportation = Column(Boolean, nullable=True)

    # -- Professional --
    applied_position = Column(String(255), nullable=True, index=True)
    applied_position_location = Column(String(255), nullable=True)
    is_open_for_relocation = Column(Boolean, nullable=True)
    years_of_experience = Column(Numeric(4, 1), nullable=True, index=True)
    is_employed = Column(Boolean, nullable=True)
    current_salary = Column(Numeric(12, 2), nullable=True, index=True)
    expected_salary_remote = Column(Numeric(12, 2), nullable=True, index=True)
    expected_salary_onsite = Column(Numeric(12, 2), nullable=True, index=True)
    notice_period = Column(String(100), nullable=True)
    is_overtime_flexible = Column(Boolean, nullable=True)
    is_contract_flexible = Column(Boolean, nullable=True)
    workplace_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    employment_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    tech_stack = Column(JSONB, server_default="[]")
    education_level_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    education_completion_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)

    # -- Dynamic & Raw --
    custom_fields = Column(JSONB, server_default="{}")
    raw_import_data = Column(JSONB, nullable=True)

    # -- HR (UI only; not set by import) --
    hr_comment = Column(Text, nullable=True)

    # -- Audit --
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_candidate_org_email"),
    )

    # -- Relationships --
    organization = relationship("Organization", back_populates="candidates")
    import_session = relationship("ImportSession", back_populates="candidates")
    residency_type = relationship("LookupOption", foreign_keys=[residency_type_id])
    marital_status = relationship("LookupOption", foreign_keys=[marital_status_id])
    passport_validity_status = relationship("LookupOption", foreign_keys=[passport_validity_status_id])
    workplace_type = relationship("LookupOption", foreign_keys=[workplace_type_id])
    employment_type = relationship("LookupOption", foreign_keys=[employment_type_id])
    education_level = relationship("LookupOption", foreign_keys=[education_level_id])
    education_completion_status = relationship("LookupOption", foreign_keys=[education_completion_status_id])


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

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
    has_transportation: Optional[bool] = None

    applied_position: Optional[str] = None
    applied_position_location: Optional[str] = None
    is_open_for_relocation: Optional[bool] = None
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


class CandidateCreate(CandidateBase):
    organization_id: int
    import_session_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    raw_import_data: Optional[Dict[str, Any]] = None


class LookupOptionLabel(BaseModel):
    id: int
    code: str
    label: str

    class Config:
        from_attributes = True


class CandidateHrCommentUpdate(BaseModel):
    """PATCH body for HR comment only."""
    hr_comment: str = Field(default="", max_length=10000)


class CandidateRead(CandidateBase):
    id: int
    organization_id: int
    import_session_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    raw_import_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    hr_comment: Optional[str] = None

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

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_lookups(
        cls,
        candidate: "Candidate",
        *,
        import_filename: Optional[str] = None,
    ) -> "CandidateRead":
        """Build a CandidateRead with resolved lookup labels.
        Pass import_filename when import_session is loaded (e.g. in get_candidate_by_id).
        import_sheet is read from the candidate model (stored at import time).
        """
        def _label(rel):
            return rel.label if rel else None

        return cls(
            id=candidate.id,
            organization_id=candidate.organization_id,
            import_session_id=candidate.import_session_id,
            applied_at=candidate.applied_at,
            full_name=candidate.full_name,
            email=candidate.email,
            date_of_birth=candidate.date_of_birth,
            nationality=candidate.nationality,
            current_address=candidate.current_address,
            residency_type_id=candidate.residency_type_id,
            marital_status_id=candidate.marital_status_id,
            number_of_dependents=candidate.number_of_dependents,
            religion_sect=candidate.religion_sect,
            passport_validity_status_id=candidate.passport_validity_status_id,
            has_transportation=candidate.has_transportation,
            applied_position=candidate.applied_position,
            applied_position_location=candidate.applied_position_location,
            is_open_for_relocation=candidate.is_open_for_relocation,
            years_of_experience=candidate.years_of_experience,
            is_employed=candidate.is_employed,
            current_salary=candidate.current_salary,
            expected_salary_remote=candidate.expected_salary_remote,
            expected_salary_onsite=candidate.expected_salary_onsite,
            notice_period=candidate.notice_period,
            is_overtime_flexible=candidate.is_overtime_flexible,
            is_contract_flexible=candidate.is_contract_flexible,
            workplace_type_id=candidate.workplace_type_id,
            employment_type_id=candidate.employment_type_id,
            tech_stack=candidate.tech_stack or [],
            education_level_id=candidate.education_level_id,
            education_completion_status_id=candidate.education_completion_status_id,
            custom_fields=candidate.custom_fields or {},
            raw_import_data=candidate.raw_import_data,
            hr_comment=candidate.hr_comment,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
            import_filename=import_filename,
            import_sheet=getattr(candidate, "import_sheet", None),
            residency_type_label=_label(candidate.residency_type),
            marital_status_label=_label(candidate.marital_status),
            passport_validity_status_label=_label(candidate.passport_validity_status),
            workplace_type_label=_label(candidate.workplace_type),
            employment_type_label=_label(candidate.employment_type),
            education_level_label=_label(candidate.education_level),
            education_completion_status_label=_label(candidate.education_completion_status),
        )


class CandidateListResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int
