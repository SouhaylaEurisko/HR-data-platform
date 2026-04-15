"""
HR stage comments ORM — one row per (candidate, stage); `entries` is JSONB.

Stage keys match ``app.constants.HR_STAGE_KEYS``.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ..config.database import Base


class CandidateStageComment(Base):
    __tablename__ = "candidate_stage_comment"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organization.id"),
        nullable=False,
    )
    stage_key = Column(String(64), nullable=False)
    entries = Column(JSONB, nullable=False, server_default="[]")
    application_status = Column(String(32), nullable=True, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "stage_key",
            name="uq_candidate_stage_comment_candidate_stage",
        ),
        Index("ix_candidate_stage_comment_candidate_id", "candidate_id"),
        Index("ix_candidate_stage_comment_organization_id", "organization_id"),
        Index("ix_candidate_stage_comment_updated_at", "updated_at"),
    )
