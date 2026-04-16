"""
Router: List custom field definitions for an organization (for filter UI).
"""

from typing import List

from fastapi import APIRouter, Depends, Query

from ..dependencies.repositories import get_custom_fields_repository
from ..repository.custom_fields_repository import CustomFieldsRepositoryProtocol
from ..schemas.custom_field import CustomFieldDefinitionOut

router = APIRouter(prefix="/api/custom-fields", tags=["custom-fields"])


@router.get("/", response_model=List[CustomFieldDefinitionOut])
def list_custom_field_definitions(
    org_id: int = Query(1, description="Organization ID"),
    custom_fields_repo: CustomFieldsRepositoryProtocol = Depends(get_custom_fields_repository),
) -> List[CustomFieldDefinitionOut]:
    """Return active custom field definitions for the organization (for filter UI)."""
    rows = custom_fields_repo.list_active_definitions_for_org(org_id)
    return [CustomFieldDefinitionOut.model_validate(r) for r in rows]
