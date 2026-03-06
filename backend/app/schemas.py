from datetime import date, datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class CandidateBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    position: Optional[str] = None
    expected_salary: Optional[float] = None
     # Text representation of expected salary (e.g., ranges like "1800-2000")
    expected_salary_text: Optional[str] = None
    years_experience: Optional[float] = Field(default=None, ge=0)
    notice_period: Optional[str] = None
    current_address: Optional[str] = None


class CandidateCreate(CandidateBase):
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_table_index: Optional[int] = None
    row_index: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None


class CandidateRead(CandidateBase):
    id: int
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_table_index: Optional[int] = None
    row_index: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateListResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int


