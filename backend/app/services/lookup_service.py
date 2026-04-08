"""
Lookup resolution — map import text to lookup_option.id (exact code or label, case-insensitive).
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.lookup import LookupOption
from ..repository import lookups_repository


def get_options_by_category(
    db: Session,
    category_code: str,
    org_id: Optional[int] = None,
) -> List[LookupOption]:
    """Active options for a category (system-wide and, when org_id given, org-specific)."""
    cat = lookups_repository.get_lookup_category_by_code(db, category_code)
    if not cat:
        return []

    return lookups_repository.fetch_active_options_for_category(
        db, category_id=cat.id, org_id=org_id
    )


def _find_option_id_by_code(options: List[LookupOption], code_lower: str) -> Optional[int]:
    for opt in options:
        if opt.code.lower() == code_lower:
            return opt.id
    return None


def resolve_lookup_value(
    db: Session,
    category_code: str,
    org_id: Optional[int],
    raw_value: str,
) -> Optional[int]:
    """
    Resolve raw text to lookup_option.id.

    Order: exact code (case-insensitive) → exact label match.
    """
    if not raw_value or not raw_value.strip():
        return None

    cleaned = raw_value.strip().lower()
    options = get_options_by_category(db, category_code, org_id)
    if not options:
        return None

    opt_id = _find_option_id_by_code(options, cleaned)
    if opt_id is not None:
        return opt_id

    for opt in options:
        if opt.label.lower() == cleaned:
            return opt.id

    return None
