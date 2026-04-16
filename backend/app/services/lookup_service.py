"""
Lookup resolution — map import text to lookup_option.id (exact code or label, case-insensitive).
"""

from typing import List, Optional, Protocol

from ..models.lookup import LookupOption
from ..repository.lookups_repository import LookupsRepositoryProtocol


class LookupServiceProtocol(Protocol):
    def get_options_by_category(
        self,
        category_code: str,
        org_id: Optional[int] = None,
    ) -> List[LookupOption]: ...
    def resolve_lookup_value(
        self,
        category_code: str,
        org_id: Optional[int],
        raw_value: str,
    ) -> Optional[int]: ...


class LookupService:
    def __init__(self, lookups_repo: LookupsRepositoryProtocol) -> None:
        self._lookups_repo = lookups_repo

    def get_options_by_category(
        self,
        category_code: str,
        org_id: Optional[int] = None,
    ) -> List[LookupOption]:
        """Active options for a category (system-wide and, when org_id given, org-specific)."""
        options, category_exists = self._lookups_repo.list_active_options_for_category_code(
            category_code,
            org_id,
        )
        if not category_exists:
            return []
        return options

    def resolve_lookup_value(
        self,
        category_code: str,
        org_id: Optional[int],
        raw_value: str,
    ) -> Optional[int]:
        if not raw_value or not raw_value.strip():
            return None

        cleaned = raw_value.strip().lower()
        options = self.get_options_by_category(category_code, org_id)
        if not options:
            return None

        opt_id = _find_option_id_by_code(options, cleaned)
        if opt_id is not None:
            return opt_id

        for opt in options:
            if opt.label.lower() == cleaned:
                return opt.id
        return None



def _find_option_id_by_code(options: List[LookupOption], code_lower: str) -> Optional[int]:
    for opt in options:
        if opt.code.lower() == code_lower:
            return opt.id
    return None


