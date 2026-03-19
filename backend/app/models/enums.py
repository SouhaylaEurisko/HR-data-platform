"""Shared enums used by ORM columns and Pydantic schemas."""

from enum import Enum


class RelocationOpenness(str, Enum):
    """
    Stored in PostgreSQL as type relocation_openness.
    Display labels: Yes, No, For missions only.
    """

    yes = "yes"
    no = "no"
    for_missions_only = "for_missions_only"


class ApplicationStatus(str, Enum):
    """HR-facing pipeline outcome; stored as VARCHAR on candidate.application_status."""

    pending = "pending"
    on_hold = "on_hold"
    rejected = "rejected"
    selected = "selected"
