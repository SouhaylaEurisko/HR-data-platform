"""Candidate profile ORM (split from legacy flat candidate table)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


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
