"""DB access for column normalization (custom field definitions)."""

from typing import List

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
