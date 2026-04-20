"""
Applications table linked to the new candidates table.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base
from .enums import RelocationOpenness, TransportationAvailability


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    import_session_id = Column(Integer, ForeignKey("import_session.id"), nullable=True, index=True)
    notice_period = Column(String(100), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    current_address = Column(Text, nullable=True)
    nationality = Column(String(100), nullable=True, index=True)
    residency_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    marital_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    number_of_dependents = Column(SmallInteger, nullable=True)
    religion_sect = Column(String(100), nullable=True)
    passport_validity_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    has_transportation = Column(
        SAEnum(
            TransportationAvailability,
            name="transportation_availability",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    applied_position = Column(String(255), nullable=True, index=True)
    applied_position_location = Column(String(255), nullable=True)
    is_open_for_relocation = Column(
        SAEnum(
            RelocationOpenness,
            name="relocation_openness",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    years_of_experience = Column(Numeric(4, 1), nullable=True, index=True)
    current_salary = Column(Numeric(12, 2), nullable=True, index=True)
    expected_salary_remote = Column(Numeric(12, 2), nullable=True, index=True)
    expected_salary_onsite = Column(Numeric(12, 2), nullable=True, index=True)
    is_overtime_flexible = Column(Boolean, nullable=True)
    is_contract_flexible = Column(Boolean, nullable=True)
    workplace_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    employment_type_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    is_employed = Column(Boolean, nullable=True)
    tech_stack = Column(JSONB, server_default="[]")
    education_level_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    education_completion_status_id = Column(Integer, ForeignKey("lookup_option.id"), nullable=True)
    custom_fields = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("CandidateProfile", back_populates="applications")
    import_session = relationship("ImportSession")
