"""Lookup category and option queries."""

from typing import Any, List, Literal, Optional, Tuple, Protocol

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..data.field_type_detection import MAX_LOOKUP_OPTIONS, non_empty_sample_strings, to_snake_case
from ..models.lookup import LookupCategory, LookupOption


def list_lookup_categories_ordered(db: Session) -> List[LookupCategory]:
    return db.query(LookupCategory).order_by(LookupCategory.code).all()


def get_lookup_category_by_code(db: Session, code: str) -> Optional[LookupCategory]:
    return db.query(LookupCategory).filter_by(code=code).first()


def list_active_options_for_category_code(
    db: Session,
    category_code: str,
    org_id: Optional[int] = None,
) -> Tuple[List[LookupOption], bool]:
    """
    Active options for ``category_code`` (system-wide and org-specific when ``org_id`` is set).

    Returns ``(options, category_exists)``. When the category is missing, ``([], False)``.
    """
    cat = get_lookup_category_by_code(db, category_code)
    if cat is None:
        return [], False
    opts = fetch_active_options_for_category(db, category_id=cat.id, org_id=org_id)
    return opts, True


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


CreateOrgLookupOptionResult = Literal["created", "category_not_found", "duplicate"]


def create_org_scoped_lookup_option_and_commit(
    db: Session,
    *,
    category_code: str,
    organization_id: int,
    code: str,
    label: str,
    display_order: int,
) -> Tuple[CreateOrgLookupOptionResult, Optional[LookupOption]]:
    """
    Insert an org-scoped lookup option if the category exists and the code is not taken.

    Commits and refreshes the new row on success.
    """
    cat = get_lookup_category_by_code(db, category_code)
    if cat is None:
        return "category_not_found", None

    existing = find_option_by_category_org_and_code(
        db, category_id=cat.id, organization_id=organization_id, code=code
    )
    if existing is not None:
        return "duplicate", None

    option = LookupOption(
        category_id=cat.id,
        organization_id=organization_id,
        code=code,
        label=label,
        display_order=display_order,
        is_active=True,
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return "created", option


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


class LookupsRepositoryProtocol(Protocol):
    def list_lookup_categories_ordered(self) -> List[LookupCategory]: ...
    def get_lookup_category_by_code(self, code: str) -> Optional[LookupCategory]: ...
    def list_active_options_for_category_code(
        self,
        category_code: str,
        org_id: Optional[int] = None,
    ) -> Tuple[List[LookupOption], bool]: ...
    def fetch_active_options_for_category(
        self,
        *,
        category_id: int,
        org_id: Optional[int] = None,
    ) -> List[LookupOption]: ...
    def find_option_by_category_org_and_code(
        self,
        *,
        category_id: int,
        organization_id: int,
        code: str,
    ) -> Optional[LookupOption]: ...
    def add_lookup_option(self, option: LookupOption) -> None: ...
    def create_org_scoped_lookup_option_and_commit(
        self,
        *,
        category_code: str,
        organization_id: int,
        code: str,
        label: str,
        display_order: int,
    ) -> Tuple[CreateOrgLookupOptionResult, Optional[LookupOption]]: ...
    def create_lookup_category_with_options_for_custom_field(
        self,
        org_id: int,
        field_key: str,
        label: str,
        values: List[Any],
    ) -> Tuple[int, LookupCategory]: ...


class LookupsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_lookup_categories_ordered(self) -> List[LookupCategory]:
        return list_lookup_categories_ordered(self._db)

    def get_lookup_category_by_code(self, code: str) -> Optional[LookupCategory]:
        return get_lookup_category_by_code(self._db, code)

    def list_active_options_for_category_code(
        self,
        category_code: str,
        org_id: Optional[int] = None,
    ) -> Tuple[List[LookupOption], bool]:
        return list_active_options_for_category_code(self._db, category_code, org_id)

    def fetch_active_options_for_category(
        self,
        *,
        category_id: int,
        org_id: Optional[int] = None,
    ) -> List[LookupOption]:
        return fetch_active_options_for_category(self._db, category_id=category_id, org_id=org_id)

    def find_option_by_category_org_and_code(
        self,
        *,
        category_id: int,
        organization_id: int,
        code: str,
    ) -> Optional[LookupOption]:
        return find_option_by_category_org_and_code(
            self._db,
            category_id=category_id,
            organization_id=organization_id,
            code=code,
        )

    def add_lookup_option(self, option: LookupOption) -> None:
        add_lookup_option(self._db, option)

    def create_org_scoped_lookup_option_and_commit(
        self,
        *,
        category_code: str,
        organization_id: int,
        code: str,
        label: str,
        display_order: int,
    ) -> Tuple[CreateOrgLookupOptionResult, Optional[LookupOption]]:
        return create_org_scoped_lookup_option_and_commit(
            self._db,
            category_code=category_code,
            organization_id=organization_id,
            code=code,
            label=label,
            display_order=display_order,
        )

    def create_lookup_category_with_options_for_custom_field(
        self,
        org_id: int,
        field_key: str,
        label: str,
        values: List[Any],
    ) -> Tuple[int, LookupCategory]:
        return create_lookup_category_with_options_for_custom_field(
            self._db,
            org_id=org_id,
            field_key=field_key,
            label=label,
            values=values,
        )
