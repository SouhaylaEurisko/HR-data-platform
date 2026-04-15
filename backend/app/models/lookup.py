"""Lookup ORM — dynamic enum pattern (category + option rows)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class LookupCategory(Base):
    """Defines the *type* of dropdown (e.g. workplace_type, marital_status)."""

    __tablename__ = "lookup_category"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    options = relationship("LookupOption", back_populates="category")


class LookupOption(Base):
    """Actual dropdown values within a category."""

    __tablename__ = "lookup_option"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("lookup_category.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=True, index=True)
    code = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    display_order = Column(SmallInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("category_id", "organization_id", "code", name="uq_lookup_option_cat_org_code"),
    )

    category = relationship("LookupCategory", back_populates="options")
