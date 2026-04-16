"""
Authentication router — login, user provisioning (HR manager), password change, and /me.
"""
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import timedelta

from ..config import config
from ..models.user import UserAccount
from ..dependencies.auth import get_current_user, require_hr_manager
from ..dependencies.services import get_auth_service
from ..schemas.user import (
    AdminUserCreate,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserRead,
)
from ..services.auth_service import (
    AuthServiceProtocol,
    AccountDeactivatedError,
    create_access_token,
)

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
    try:
        user = auth_service.authenticate_user(str(body.email), body.password)
    except AccountDeactivatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact an HR manager.",
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    try:
        user_create = UserCreate(
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            organization_id=current_user.organization_id,
            role=body.role,
        )
        user = auth_service.create_user(user_create)
        return UserRead.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
):
    try:
        auth_service.change_user_password(
            current_user,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    user = auth_service.set_user_active(
        user_id,
        current_user.organization_id,
        active=body.is_active,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization.",
        )
    return UserRead.model_validate(user)
