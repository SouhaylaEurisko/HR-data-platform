"""
Candidate models — SQLAlchemy ORM table + Pydantic request/response schemas.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Date, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from ..config.database import Base


# ──────────────────────────────────────────────
# SQLAlchemy ORM models
# ──────────────────────────────────────────────

class DataSource(Base):
    """Represents the source file/sheet/table combination from which candidates are imported."""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), nullable=False, index=True)
    source_sheet = Column(String(255), nullable=False, index=True)
    source_table_index = Column(Integer, nullable=False)
    
    # Metadata
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Unique constraint: same file+sheet+table combination
    __table_args__ = (
        UniqueConstraint('source_file', 'source_sheet', 'source_table_index', 
                        name='uq_data_source_file_sheet_table'),
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to data_source
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True, index=True)
    row_index = Column(Integer, nullable=True)  # Row within the table
    
    # Relationship
    data_source = relationship("DataSource", backref="candidates")

    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    nationality = Column(String(255), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True, index=True)
    position = Column(String(255), nullable=True, index=True)
    expected_salary = Column(Float, nullable=True, index=True)
    expected_salary_text = Column(String(255), nullable=True)
    years_experience = Column(Float, nullable=True, index=True)
    notice_period = Column(String(255), nullable=True)
    current_address = Column(String(255), nullable=True)
    raw_data = Column(JSON, nullable=True)

    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class CandidateBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    position: Optional[str] = None
    expected_salary: Optional[float] = None
    expected_salary_text: Optional[str] = None
    years_experience: Optional[float] = Field(default=None, ge=0)
    notice_period: Optional[str] = None
    current_address: Optional[str] = None


# ──────────────────────────────────────────────
# DataSource Pydantic schemas
# ──────────────────────────────────────────────

class DataSourceRead(BaseModel):
    id: int
    source_file: str
    source_sheet: str
    source_table_index: int
    imported_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Candidate Pydantic schemas
# ──────────────────────────────────────────────

class CandidateCreate(CandidateBase):
    data_source_id: Optional[int] = None
    row_index: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None


class CandidateRead(CandidateBase):
    id: int
    data_source_id: Optional[int] = None
    row_index: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    # Include source info for backward compatibility
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_table_index: Optional[int] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm_with_source(cls, candidate):
        """Create CandidateRead with source info populated from relationship."""
        data = {
            "id": candidate.id,
            "full_name": candidate.full_name,
            "email": candidate.email,
            "nationality": candidate.nationality,
            "date_of_birth": candidate.date_of_birth,
            "position": candidate.position,
            "expected_salary": candidate.expected_salary,
            "expected_salary_text": candidate.expected_salary_text,
            "years_experience": candidate.years_experience,
            "notice_period": candidate.notice_period,
            "current_address": candidate.current_address,
            "raw_data": candidate.raw_data,
            "data_source_id": candidate.data_source_id,
            "row_index": candidate.row_index,
            "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
            "source_file": candidate.data_source.source_file if candidate.data_source else None,
            "source_sheet": candidate.data_source.source_sheet if candidate.data_source else None,
            "source_table_index": candidate.data_source.source_table_index if candidate.data_source else None,
        }
        return cls(**data)


class CandidateListResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int
