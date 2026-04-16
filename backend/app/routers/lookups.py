"""
Router: Lookup endpoints for fetching and creating dropdown options.
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies.repositories import get_lookups_repository
from ..models.user import UserAccount
from ..dependencies.auth import get_current_user, require_hr_manager
from ..repository.lookups_repository import LookupsRepositoryProtocol
from ..schemas.lookup import CreateLookupOptionRequest, LookupCategoryOut, LookupOptionOut

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


@router.get("/", summary="List all lookup categories")
def list_categories(
    lookups_repo: LookupsRepositoryProtocol = Depends(get_lookups_repository),
) -> List[LookupCategoryOut]:
    cats = lookups_repo.list_lookup_categories_ordered()
    return [LookupCategoryOut.model_validate(c) for c in cats]


@router.get("/{category_code}", summary="Get options for a lookup category")
def get_category_options(
    category_code: str,
    org_id: Optional[int] = Query(None),
    lookups_repo: LookupsRepositoryProtocol = Depends(get_lookups_repository),
) -> List[LookupOptionOut]:
    options, category_exists = lookups_repo.list_active_options_for_category_code(
        category_code, org_id
    )
    if not options and not category_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_code}' not found.",
        )
    return [LookupOptionOut.model_validate(o) for o in options]


@router.post("/{category_code}", summary="Create a new org-specific lookup option", status_code=201)
def create_option(
    category_code: str,
    body: CreateLookupOptionRequest,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    org_id: int = Query(..., description="Organization ID"),
    lookups_repo: LookupsRepositoryProtocol = Depends(get_lookups_repository),
) -> LookupOptionOut:
    require_hr_manager(current_user)
    outcome, option = lookups_repo.create_org_scoped_lookup_option_and_commit(
        category_code=category_code,
        organization_id=org_id,
        code=body.code,
        label=body.label,
        display_order=body.display_order,
    )
    if outcome == "category_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_code}' not found.",
        )
    if outcome == "duplicate":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Option '{body.code}' already exists in category '{category_code}' for this org.",
        )
    if option is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lookup option was not persisted.",
        )
    return LookupOptionOut.model_validate(option)
