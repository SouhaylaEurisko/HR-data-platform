"""
Router: List custom field definitions for an organization (for filter UI).
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.custom_field import CustomFieldDefinitionOut
from ..repository import custom_fields_repository

router = APIRouter(prefix="/api/custom-fields", tags=["custom-fields"])


@router.get("/", response_model=List[CustomFieldDefinitionOut])
def list_custom_field_definitions(
    org_id: int = Query(1, description="Organization ID"),
    db: Session = Depends(get_db),
) -> List[CustomFieldDefinitionOut]:
    """Return active custom field definitions for the organization (for filter UI)."""
    rows = custom_fields_repository.list_active_definitions_for_org(db, org_id)
    return [CustomFieldDefinitionOut.model_validate(r) for r in rows]
