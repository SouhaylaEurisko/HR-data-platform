"""
HR stage comments — one row per (candidate, stage); `entries` is a JSONB array of
{ "text": "...", "created_at": "<ISO-8601>" } (oldest → newest).

Stage keys match `data.hr_stage_comments.HR_STAGE_KEYS`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ..config.database import Base
from ..data.hr_stage_comments import HR_STAGE_KEYS
from .enums import ApplicationStatus

_MAX_LEN = 10000

StageKeyLiteral = Literal["pre_screening", "technical_interview", "hr_interview", "offer_stage"]


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


class HrStageCommentEntryRead(BaseModel):
    id: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class HrStageCommentsRead(BaseModel):
    pre_screening: List[HrStageCommentEntryRead] = Field(default_factory=list)
    technical_interview: List[HrStageCommentEntryRead] = Field(default_factory=list)
    hr_interview: List[HrStageCommentEntryRead] = Field(default_factory=list)
    offer_stage: List[HrStageCommentEntryRead] = Field(default_factory=list)


class CandidateHrStageCommentCreate(BaseModel):
    stage: StageKeyLiteral
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _trim_and_cap(cls, v: Any) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        return s[:_MAX_LEN] if len(s) > _MAX_LEN else s

    @model_validator(mode="after")
    def _require_text(self) -> CandidateHrStageCommentCreate:
        if not self.text:
            raise ValueError("Comment text cannot be empty")
        return self


class CandidateHrStageCommentResponse(BaseModel):
    candidate_id: int
    stage: StageKeyLiteral
    entry: HrStageCommentEntryRead


class CandidateHrStageCommentsUpdateResponse(BaseModel):
    """Returned after appending an HR stage comment — merge into client candidate state."""

    hr_stage_comments: HrStageCommentsRead


class CandidateApplicationStatusResponse(BaseModel):
    """Returned from PATCH .../application-status — merge `application_status` into client state."""

    candidate_id: int
    application_status: ApplicationStatus


def empty_hr_stage_comments_read() -> HrStageCommentsRead:
    return HrStageCommentsRead(
        pre_screening=[],
        technical_interview=[],
        hr_interview=[],
        offer_stage=[],
    )


def _parse_created_at(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _entries_json_to_reads(entries: Any) -> List[HrStageCommentEntryRead]:
    if not isinstance(entries, list):
        return []
    out: List[HrStageCommentEntryRead] = []
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        try:
            ct = _parse_created_at(item.get("created_at"))
        except (TypeError, ValueError):
            ct = datetime.now(timezone.utc)
        out.append(HrStageCommentEntryRead(id=i, text=text, created_at=ct))
    return out


def json_rows_to_hr_stage_comments_read(rows: list[Any]) -> HrStageCommentsRead:
    """Build API shape from ORM rows (one row per stage with JSONB `entries`)."""
    buckets: dict[str, List[HrStageCommentEntryRead]] = {k: [] for k in HR_STAGE_KEYS}
    for r in rows:
        sk = getattr(r, "stage_key", None)
        if sk not in buckets:
            continue
        raw = _entries_json_to_reads(getattr(r, "entries", None))
        raw.sort(key=lambda e: e.created_at)
        buckets[sk] = [
            HrStageCommentEntryRead(id=i, text=e.text, created_at=e.created_at)
            for i, e in enumerate(raw)
        ]
    return HrStageCommentsRead(
        pre_screening=buckets["pre_screening"],
        technical_interview=buckets["technical_interview"],
        hr_interview=buckets["hr_interview"],
        offer_stage=buckets["offer_stage"],
    )


def hr_stage_comments_latest_only(full: HrStageCommentsRead) -> HrStageCommentsRead:
    """For list API: only the last entry per stage (smaller payload)."""

    def take_last(xs: List[HrStageCommentEntryRead]) -> List[HrStageCommentEntryRead]:
        if not xs:
            return []
        last = xs[-1]
        return [HrStageCommentEntryRead(id=0, text=last.text, created_at=last.created_at)]

    return HrStageCommentsRead(
        pre_screening=take_last(full.pre_screening),
        technical_interview=take_last(full.technical_interview),
        hr_interview=take_last(full.hr_interview),
        offer_stage=take_last(full.offer_stage),
    )
