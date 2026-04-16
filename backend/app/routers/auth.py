"""
Authentication router — login, user provisioning (HR manager), password change, and /me.
"""
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from datetime import timedelta

from ..config import config
from ..exceptions import BusinessRuleError, InvalidCredentialsError, NotFoundError
from ..models.user import UserAccount
from ..dependencies.auth import get_current_user, require_hr_manager
from ..dependencies.services import get_auth_service
from ..factories.user_factory import user_create_from_admin
from ..schemas.user import (
    AdminUserCreate,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserRead,
)
from ..services.auth_service import AuthServiceProtocol, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login to retrieve Bearer token",
    response_description="A Bearer token, token type, and user object.",
)
async def login(
    body: LoginRequest = Body(..., description="Login credentials (`email` and `password`)"),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    """
    Authenticate user with `email` and `password` fields and return an access token and current user.
    Adjusted for improved reliability and clarity.
    """
    user = auth_service.authenticate_user(str(body.email), body.password)

    if not user:
        raise InvalidCredentialsError()

    access_token = create_access_token(
        subject_user_id=user.id,
        email=user.email,
        organization_id=user.organization_id,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    expires_in = int(timedelta(minutes=config.jwt_expire_minutes).total_seconds())

    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/users", response_model=UserRead)
async def create_user_as_admin(
    body: AdminUserCreate,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    """
    Create a user in the caller's organization. Only HR managers.
    Does not return a token — the new user must sign in separately.
    """
    require_hr_manager(current_user)
    user_create = user_create_from_admin(
        body,
        organization_id=current_user.organization_id,
    )
    user = auth_service.create_user(user_create)
    return UserRead.model_validate(user)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    auth_service.change_user_password(
        current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return {"ok": True}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
):
    return UserRead.model_validate(current_user)


@router.get("/users", response_model=List[UserRead])
async def list_org_users(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    """List all users in the caller's organization. HR managers only."""
    require_hr_manager(current_user)
    users = auth_service.list_users(current_user.organization_id)
    return [UserRead.model_validate(u) for u in users]


class SetActiveBody(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def toggle_user_status(
    user_id: int,
    body: SetActiveBody,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    """Activate or deactivate a user. HR managers only. Cannot deactivate yourself."""
    require_hr_manager(current_user)
    if user_id == current_user.id:
        raise BusinessRuleError("You cannot deactivate your own account.")
    user = auth_service.set_user_active(
        user_id,
        current_user.organization_id,
        active=body.is_active,
    )
    if user is None:
        raise NotFoundError("User not found in your organization.")
    return UserRead.model_validate(user)
