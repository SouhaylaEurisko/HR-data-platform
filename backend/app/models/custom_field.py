"""
CustomFieldDefinition -- registry for org-specific dynamic fields
stored in the candidate.custom_fields JSONB column.
"""

from sqlalchemy import (
    Boolean, Column, Integer, SmallInteger, String,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class CustomFieldDefinition(Base):
    __tablename__ = "custom_field_definition"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    field_key = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, number, date, boolean, lookup
    lookup_category_id = Column(Integer, ForeignKey("lookup_category.id"), nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(SmallInteger, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "field_key", name="uq_custom_field_org_key"),
    )

    organization = relationship("Organization", back_populates="custom_field_definitions")
    lookup_category = relationship("LookupCategory")
