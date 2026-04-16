"""DB access for column normalization (custom field definitions)."""

from typing import List, Protocol

from sqlalchemy.orm import Session

from ..models.custom_field import CustomFieldDefinition


def fetch_active_custom_field_definitions(
    db: Session, org_id: int
) -> List[CustomFieldDefinition]:
    return (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, is_active=True)
        .all()
    )


class ColumnNormalizerRepositoryProtocol(Protocol):
    def fetch_active_custom_field_definitions(self, org_id: int) -> List[CustomFieldDefinition]: ...


class ColumnNormalizerRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def fetch_active_custom_field_definitions(self, org_id: int) -> List[CustomFieldDefinition]:
        return fetch_active_custom_field_definitions(self._db, org_id)
