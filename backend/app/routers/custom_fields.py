"""
Router: List custom field definitions for an organization (for filter UI).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.custom_field import CustomFieldDefinition

router = APIRouter(prefix="/api/custom-fields", tags=["custom-fields"])


class CustomFieldDefinitionOut(BaseModel):
    id: int
    field_key: str
    label: str
    field_type: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CustomFieldDefinitionOut])
def list_custom_field_definitions(
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> List[CustomFieldDefinitionOut]:
    """Return active custom field definitions for the organization (for filter UI)."""
    rows = (
        db.query(CustomFieldDefinition)
        .filter_by(organization_id=org_id, is_active=True)
        .order_by(CustomFieldDefinition.display_order, CustomFieldDefinition.label)
        .all()
    )
    return [CustomFieldDefinitionOut.model_validate(r) for r in rows]
