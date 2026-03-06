from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Date
from sqlalchemy.dialects.sqlite import JSON

from .db import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), nullable=True)
    source_sheet = Column(String(255), nullable=True, index=True)
    source_table_index = Column(Integer, nullable=True)
    row_index = Column(Integer, nullable=True)

    full_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    nationality = Column(String(255), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True, index=True)
    position = Column(String(255), nullable=True, index=True)
    # Numeric expected salary (used for filtering / sorting)
    expected_salary = Column(Float, nullable=True, index=True)
    # Text version of expected salary (e.g., ranges like "1800-2000")
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


