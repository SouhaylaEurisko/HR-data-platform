"""Centralized application constants (grouped by domain)."""

from __future__ import annotations

from typing import Final, FrozenSet


class Auth:
    HR_MANAGER_ROLE: Final[str] = "hr_manager"
    HR_VIEWER_ROLE: Final[str] = "hr_viewer"


class Analytics:
    UNSET_FILTER_VALUE: Final[str] = "__unset__"
    UNSET_STATUS_KEY: Final[str] = "unset"
    TOP_N_BUCKETS: Final[int] = 10
    RECENT_APPLICATION_DAYS: Final[int] = 30


STATUS_LABELS: Final[dict[str, str]] = {
    "pending": "Pending",
    "on_hold": "On hold",
    "rejected": "Rejected",
    "selected": "Selected",
    Analytics.UNSET_STATUS_KEY: "Not set",
}

# HR pipeline stage keys (API / JSONB). Order: first key is default when seeding stage rows.
HR_STAGE_KEYS: Final[tuple[str, ...]] = (
    "pre_screening",
    "technical_interview",
    "hr_interview",
    "offer_stage",
)


class ResumeUpload:
    MAX_FILE_BYTES: Final[int] = 10 * 1024 * 1024
    ALLOWED_CONTENT_TYPES: Final[FrozenSet[str]] = frozenset({"application/pdf"})


class ResumeParser:
    MAX_PDF_PAGES: Final[int] = 5
    RENDER_DPI: Final[int] = 200


class ColumnNormalizer:
    LLM_DEFAULT_CONFIDENCE: Final[float] = 0.5
    LLM_AUTO_MATCH_MIN: Final[float] = 0.90
    LLM_SUGGEST_MIN: Final[float] = 0.70


class CandidateList:
    DEFAULT_PAGE: Final[int] = 1
    DEFAULT_PAGE_SIZE: Final[int] = 20
    MAX_PAGE_SIZE: Final[int] = 100
    CHAT_SORT_BY_KEYS: Final[tuple[str, ...]] = ("created_at", "full_name")
    PROFILE_SORT_BY_KEYS: Final[tuple[str, ...]] = (
        "created_at",
        "full_name",
        "email",
        "date_of_birth",
        "applied_position",
    )
