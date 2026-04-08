"""
Router: Lookup endpoints for fetching and creating dropdown options.
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.lookup import LookupCategoryOut, LookupOption, LookupOptionOut, CreateLookupOptionRequest
from ..models.user import UserAccount
from ..routers.auth import get_current_user, require_hr_manager
from ..repository import lookups_repository
from ..services.lookup_service import get_options_by_category

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


@router.get("/", summary="List all lookup categories")
def list_categories(db: Session = Depends(get_db)) -> List[LookupCategoryOut]:
    cats = lookups_repository.list_lookup_categories_ordered(db)
    return [LookupCategoryOut.model_validate(c) for c in cats]


@router.get("/{category_code}", summary="Get options for a lookup category")
def get_category_options(
    category_code: str,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> List[LookupOptionOut]:
    options = get_options_by_category(db, category_code, org_id)
    if not options:
        cat = lookups_repository.get_lookup_category_by_code(db, category_code)
        if not cat:
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
    db: Session = Depends(get_db),
) -> LookupOptionOut:
    require_hr_manager(current_user)
    cat = lookups_repository.get_lookup_category_by_code(db, category_code)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_code}' not found.",
        )

    existing = lookups_repository.find_option_by_category_org_and_code(
        db, category_id=cat.id, organization_id=org_id, code=body.code
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Option '{body.code}' already exists in category '{category_code}' for this org.",
        )

    option = LookupOption(
        category_id=cat.id,
        organization_id=org_id,
        code=body.code,
        label=body.label,
        display_order=body.display_order,
        is_active=True,
    )
    lookups_repository.add_lookup_option(db, option)
    db.commit()
    db.refresh(option)
    return LookupOptionOut.model_validate(option)
