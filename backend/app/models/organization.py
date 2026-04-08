"""
Organization model -- multi-tenancy root.
Every piece of data belongs to an organization.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class Organization(Base):
    __tablename__ = "organization"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    settings = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("UserAccount", back_populates="organization")
    candidates = relationship("CandidateProfile", back_populates="organization")
    import_sessions = relationship("ImportSession", back_populates="organization")
    custom_field_definitions = relationship("CustomFieldDefinition", back_populates="organization")
