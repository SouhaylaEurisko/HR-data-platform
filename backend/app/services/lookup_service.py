"""
Lookup resolution — map raw import text to lookup_option.id (code, label, then aliases).
"""

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..data.lookup_aliases import LOOKUP_ALIASES
from ..models.lookup import LookupCategory, LookupOption


def get_options_by_category(
    db: Session,
    category_code: str,
    org_id: Optional[int] = None,
) -> List[LookupOption]:
    """Active options for a category (system-wide and, when org_id given, org-specific)."""
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

    Order: exact code (case-insensitive) → exact label → alias map → canonical code.
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

    resolved_code = LOOKUP_ALIASES.get(category_code, {}).get(cleaned)
    if resolved_code:
        return _find_option_id_by_code(options, resolved_code.lower())

    return None
