"""Analytics router — read-only KPIs scoped to the authenticated user's organization."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import get_db
from ..schemas.analytics import AnalyticsOverviewResponse
from ..models.user import UserAccount
from ..routers.auth import get_current_user
from ..services.analytics_service import get_analytics_overview

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    status: Annotated[
        Optional[str],
        Query(description="Exact application status filter; use __unset__ to match blank status"),
    ] = None,
    position: Annotated[
        Optional[str],
        Query(description="Exact applied position filter; use __unset__ to match blank position"),
    ] = None,
    location: Annotated[
        Optional[str],
        Query(description="Exact applied position location filter; use __unset__ to match blank location"),
    ] = None,
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """
    Aggregated candidate metrics for the current user's organization.
    Available to all authenticated roles (including hr_viewer).
    """
    return get_analytics_overview(
        db,
        current_user.organization_id,
        status=status,
        position=position,
        location=location,
    )
