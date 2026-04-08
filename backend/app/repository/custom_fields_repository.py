"""Custom field definition queries."""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.custom_field import CustomFieldDefinition


def get_definition_by_org_and_field_key(
    db: Session, org_id: int, field_key: str
) -> Optional[CustomFieldDefinition]:
    return (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, field_key=field_key)
        .first()
    )


def add_custom_field_definition(db: Session, definition: CustomFieldDefinition) -> None:
    db.add(definition)
    db.flush()


def list_active_definitions_for_org(db: Session, org_id: int) -> List[CustomFieldDefinition]:
    return (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, is_active=True)
        .order_by(CustomFieldDefinition.display_order, CustomFieldDefinition.label)
        .all()
    )
