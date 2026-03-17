"""
Lookup resolution service — resolves raw text values to lookup_option IDs
using case-insensitive matching and a built-in alias map.
"""

from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.lookup import LookupCategory, LookupOption


# ──────────────────────────────────────────────
# Alias map: common abbreviations → lookup codes
# ──────────────────────────────────────────────

LOOKUP_ALIASES: Dict[str, Dict[str, str]] = {
    "workplace_type": {
        "wfh": "remote",
        "work from home": "remote",
        "on-site": "onsite",
        "on site": "onsite",
        "office": "onsite",
        "in-office": "onsite",
        "mix": "hybrid",
        "mixed": "hybrid",
        "flexible": "hybrid",
    },
    "employment_type": {
        "ft": "full_time",
        "full time": "full_time",
        "pt": "part_time",
        "part time": "part_time",
        "contract": "contractual",
        "contractor": "contractual",
        "freelance": "contractual",
    },
    "employment_status": {
        "working": "employed",
        "not employed": "unemployed",
        "jobless": "unemployed",
        "self-employed": "freelance",
        "self employed": "freelance",
        "studying": "student",
    },
    "residency_type": {
        "local": "citizen",
        "national": "citizen",
        "pr": "permanent_resident",
        "perm resident": "permanent_resident",
        "work permit": "work_visa",
        "tourist": "tourist_visa",
        "student": "student_visa",
    },
    "marital_status": {
        "not married": "single",
        "unmarried": "single",
        "wed": "married",
    },
    "education_level": {
        "hs": "high_school",
        "high school diploma": "high_school",
        "secondary": "high_school",
        "bs": "bachelor",
        "ba": "bachelor",
        "bsc": "bachelor",
        "bachelors": "bachelor",
        "bachelor's": "bachelor",
        "undergraduate": "bachelor",
        "ms": "master",
        "ma": "master",
        "msc": "master",
        "masters": "master",
        "master's": "master",
        "mba": "master",
        "phd": "doctorate",
        "ph.d": "doctorate",
        "doctoral": "doctorate",
    },
    "education_completion": {
        "done": "completed",
        "finished": "completed",
        "ongoing": "in_progress",
        "current": "in_progress",
        "not completed": "incomplete",
        "partial": "incomplete",
        "dropped": "dropped_out",
        "quit": "dropped_out",
    },
    "passport_validity": {
        "yes": "valid",
        "active": "valid",
        "no": "no_passport",
        "none": "no_passport",
        "renewing": "renewal_in_progress",
        "pending renewal": "renewal_in_progress",
    },
}


def get_options_by_category(
    db: Session,
    category_code: str,
    org_id: Optional[int] = None,
) -> List[LookupOption]:
    """Return all active options for a category (system-wide + org-specific)."""
    cat = db.query(LookupCategory).filter_by(code=category_code).first()
    if not cat:
        return []

    query = db.query(LookupOption).filter(
        LookupOption.category_id == cat.id,
        LookupOption.is_active.is_(True),
    )
    if org_id is not None:
        query = query.filter(
            or_(
                LookupOption.organization_id.is_(None),
                LookupOption.organization_id == org_id,
            )
        )
    else:
        query = query.filter(LookupOption.organization_id.is_(None))

    return query.order_by(LookupOption.display_order).all()


def resolve_lookup_value(
    db: Session,
    category_code: str,
    org_id: Optional[int],
    raw_value: str,
) -> Optional[int]:
    """
    Resolve a raw text value to a lookup_option.id.

    Resolution order:
      1. Exact code match (case-insensitive)
      2. Exact label match (case-insensitive)
      3. Alias map match
    """
    if not raw_value or not raw_value.strip():
        return None

    cleaned = raw_value.strip().lower()

    options = get_options_by_category(db, category_code, org_id)
    if not options:
        return None

    # 1. Exact code match
    for opt in options:
        if opt.code.lower() == cleaned:
            return opt.id

    # 2. Exact label match
    for opt in options:
        if opt.label.lower() == cleaned:
            return opt.id

    # 3. Alias map
    aliases = LOOKUP_ALIASES.get(category_code, {})
    resolved_code = aliases.get(cleaned)
    if resolved_code:
        for opt in options:
            if opt.code.lower() == resolved_code:
                return opt.id

    return None
