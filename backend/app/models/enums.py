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


class TransportationAvailability(str, Enum):
    """
    Stored in PostgreSQL as type transportation_availability.
    Display labels: YES, NO, Only Open for Remote Opportunities.
    """

    yes = "yes"
    no = "no"
    only_open_for_remote_opportunities = "only_open_for_remote_opportunities"


class ApplicationStatus(str, Enum):
    """HR-facing pipeline outcome; stored as VARCHAR on candidate.application_status."""

    pending = "pending"
    on_hold = "on_hold"
    rejected = "rejected"
    selected = "selected"
