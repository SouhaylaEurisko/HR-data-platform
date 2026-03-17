"""
Router: Lookup endpoints for fetching and creating dropdown options.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.lookup import LookupCategory, LookupOption
from ..services.lookup_service import get_options_by_category

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


class LookupOptionOut(BaseModel):
    id: int
    code: str
    label: str
    display_order: int
    is_active: bool

    class Config:
        from_attributes = True


class LookupCategoryOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    is_system: bool

    class Config:
        from_attributes = True


class CreateLookupOptionRequest(BaseModel):
    code: str
    label: str
    display_order: int = 0


@router.get("/", summary="List all lookup categories")
def list_categories(db: Session = Depends(get_db)) -> List[LookupCategoryOut]:
    cats = db.query(LookupCategory).order_by(LookupCategory.code).all()
    return [LookupCategoryOut.model_validate(c) for c in cats]


@router.get("/{category_code}", summary="Get options for a lookup category")
def get_category_options(
    category_code: str,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> List[LookupOptionOut]:
    options = get_options_by_category(db, category_code, org_id)
    if not options:
        cat = db.query(LookupCategory).filter_by(code=category_code).first()
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
    org_id: int = Query(..., description="Organization ID"),
    db: Session = Depends(get_db),
) -> LookupOptionOut:
    cat = db.query(LookupCategory).filter_by(code=category_code).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_code}' not found.",
        )

    existing = (
        db.query(LookupOption)
        .filter_by(category_id=cat.id, organization_id=org_id, code=body.code)
        .first()
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
    db.add(option)
    db.commit()
    db.refresh(option)
    return LookupOptionOut.model_validate(option)
