"""
Orchestrate custom field creation during import (type detection + repositories).
"""

from typing import Any, List, Optional, Tuple, Protocol

from ..data.field_type_detection import detect_field_type, to_snake_case
from ..models.custom_field import CustomFieldDefinition
from ..models.lookup import LookupCategory
from ..repository.custom_fields_repository import CustomFieldsRepositoryProtocol
from ..repository.lookups_repository import LookupsRepositoryProtocol


class CustomFieldTypeServiceProtocol(Protocol):
    def create_custom_field(
        self,
        org_id: int,
        label: str,
        values: List[Any],
    ) -> Tuple[CustomFieldDefinition, Optional[LookupCategory]]: ...


class CustomFieldTypeService:
    def __init__(
        self,
        custom_fields_repo: CustomFieldsRepositoryProtocol,
        lookups_repo: LookupsRepositoryProtocol,
    ) -> None:
        self._custom_fields_repo = custom_fields_repo
        self._lookups_repo = lookups_repo

    def create_custom_field(
        self,
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

        existing = self._custom_fields_repo.get_definition_by_org_and_field_key(
            org_id,
            field_key,
        )
        if existing:
            return existing, None

        lookup_category: Optional[LookupCategory] = None
        lookup_category_id: Optional[int] = None

        if field_type == "lookup":
            lookup_category_id, lookup_category = (
                self._lookups_repo.create_lookup_category_with_options_for_custom_field(
                    org_id,
                    field_key,
                    label,
                    values,
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
        self._custom_fields_repo.add_custom_field_definition(cfd)

        return cfd, lookup_category

