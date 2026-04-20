"""Shared field mapping helpers for candidate read / patch assembly."""

from typing import Any, Optional

from ..models.enums import ApplicationStatus, TransportationAvailability
from ..schemas.candidate import RelatedApplicationSummary


def transport_enum_from_value(value: Any) -> Optional[TransportationAvailability]:
    if value is None:
        return None
    if isinstance(value, TransportationAvailability):
        return value
    if isinstance(value, bool):
        return TransportationAvailability.yes if value else TransportationAvailability.no
    text = str(value).strip().lower()
    for member in TransportationAvailability:
        if text == member.value or text == member.name.lower():
            return member
    return None


def optional_application_status(raw: Optional[str]) -> Optional[ApplicationStatus]:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().lower()
    for member in ApplicationStatus:
        if member.value == s:
            return member
    return None


def resolved_nationality_from_application(application: Any) -> Optional[str]:
    """Prefer ``applications.nationality``; fall back to legacy ``custom_fields``."""
    if application is None:
        return None
    if application.nationality and str(application.nationality).strip():
        return str(application.nationality).strip()
    v = (dict(application.custom_fields or {})).get("nationality")
    if v is not None and str(v).strip():
        return str(v).strip()
    return None


def related_summaries_from_group_rows(rows: list[Any]) -> list[RelatedApplicationSummary]:
    return [
        RelatedApplicationSummary(
            id=r.id,
            applied_position=r.applied_position,
            applied_at=r.applied_at,
            created_at=r.created_at,
        )
        for r in rows
    ]
