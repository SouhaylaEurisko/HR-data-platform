"""Lookup category and option queries."""

from typing import Any, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..data.field_type_detection import MAX_LOOKUP_OPTIONS, non_empty_sample_strings, to_snake_case
from ..models.lookup import LookupCategory, LookupOption


def list_lookup_categories_ordered(db: Session) -> List[LookupCategory]:
    return db.query(LookupCategory).order_by(LookupCategory.code).all()


def get_lookup_category_by_code(db: Session, code: str) -> Optional[LookupCategory]:
    return db.query(LookupCategory).filter_by(code=code).first()


def fetch_active_options_for_category(
    db: Session,
    *,
    category_id: int,
    org_id: Optional[int] = None,
) -> List[LookupOption]:
    """Active options for a category (system-wide and, when org_id given, org-specific)."""
    query = db.query(LookupOption).filter(
        LookupOption.category_id == category_id,
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


def find_option_by_category_org_and_code(
    db: Session,
    *,
    category_id: int,
    organization_id: int,
    code: str,
) -> Optional[LookupOption]:
    return (
        db.query(LookupOption)
        .filter_by(category_id=category_id, organization_id=organization_id, code=code)
        .first()
    )


def add_lookup_option(db: Session, option: LookupOption) -> None:
    db.add(option)


def create_lookup_category_with_options_for_custom_field(
    db: Session,
    org_id: int,
    field_key: str,
    label: str,
    values: List[Any],
) -> Tuple[int, LookupCategory]:
    """Create LookupCategory + org-scoped options for a lookup-type custom field (import)."""
    non_empty = non_empty_sample_strings(values)
    unique_vals = sorted({v.strip() for v in non_empty})

    lookup_category = LookupCategory(
        code=f"custom_{field_key}",
        label=label,
        description=f"Auto-detected lookup for custom field '{label}'",
        is_system=False,
    )
    db.add(lookup_category)
    db.flush()

    for i, val in enumerate(unique_vals[:MAX_LOOKUP_OPTIONS], start=1):
        db.add(
            LookupOption(
                category_id=lookup_category.id,
                organization_id=org_id,
                code=to_snake_case(val),
                label=val,
                display_order=i,
                is_active=True,
            )
        )

    return lookup_category.id, lookup_category
