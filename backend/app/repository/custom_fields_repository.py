"""Custom field definition queries."""

from typing import List, Optional, Protocol

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


class CustomFieldsRepositoryProtocol(Protocol):
    def get_definition_by_org_and_field_key(
        self,
        org_id: int,
        field_key: str,
    ) -> Optional[CustomFieldDefinition]: ...
    def add_custom_field_definition(self, definition: CustomFieldDefinition) -> None: ...
    def list_active_definitions_for_org(self, org_id: int) -> List[CustomFieldDefinition]: ...


class CustomFieldsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_definition_by_org_and_field_key(
        self,
        org_id: int,
        field_key: str,
    ) -> Optional[CustomFieldDefinition]:
        return get_definition_by_org_and_field_key(self._db, org_id, field_key)

    def add_custom_field_definition(self, definition: CustomFieldDefinition) -> None:
        add_custom_field_definition(self._db, definition)

    def list_active_definitions_for_org(self, org_id: int) -> List[CustomFieldDefinition]:
        return list_active_definitions_for_org(self._db, org_id)
