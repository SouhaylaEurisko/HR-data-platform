"""
Orchestrate custom field creation during import (type detection + repositories).
"""

from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..data.field_type_detection import detect_field_type, to_snake_case
from ..models.custom_field import CustomFieldDefinition
from ..models.lookup import LookupCategory
from ..repository import custom_fields_repository, lookups_repository


def create_custom_field(
    db: Session,
    org_id: int,
    label: str,
    values: List[Any],
) -> Tuple[CustomFieldDefinition, Optional[LookupCategory]]:
    """
    Detect type, create CustomFieldDefinition, and optionally
    LookupCategory + LookupOptions when type is lookup.
    """
    field_type = detect_field_type(values)
    field_key = to_snake_case(label)

    existing = custom_fields_repository.get_definition_by_org_and_field_key(
        db, org_id, field_key
    )
    if existing:
        return existing, None

    lookup_category: Optional[LookupCategory] = None
    lookup_category_id: Optional[int] = None

    if field_type == "lookup":
        lookup_category_id, lookup_category = (
            lookups_repository.create_lookup_category_with_options_for_custom_field(
                db, org_id, field_key, label, values
            )
        )

    cfd = CustomFieldDefinition(
        organization_id=org_id,
        field_key=field_key,
        label=label,
        field_type=field_type,
        lookup_category_id=lookup_category_id,
        is_required=False,
        is_active=True,
    )
    custom_fields_repository.add_custom_field_definition(db, cfd)

    return cfd, lookup_category
