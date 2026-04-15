"""
Authentication router — login, user provisioning (HR manager), password change, and /me.
"""
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import timedelta

from ..config import get_db, config
from ..constants import Auth
from ..models.user import UserAccount
from ..schemas.user import (
    AdminUserCreate,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserRead,
)
from ..services.auth_service import (
    AccountDeactivatedError,
    TokenExpiredError,
    authenticate_user,
    change_user_password,
    create_access_token,
    create_user,
    get_user_by_id,
    get_user_id_from_token,
    list_users,
    set_user_active,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> UserAccount:
    token = credentials.credentials if credentials is not None else None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        user_id = get_user_id_from_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except ValueError:
        raise credentials_exception from None

    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact an HR manager.",
        )
    return user


def require_hr_manager(current_user: UserAccount) -> None:
    if current_user.role != Auth.HR_MANAGER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR managers can perform this action.",
        )



@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login to retrieve Bearer token",
    response_description="A Bearer token, token type, and user object.",
)
async def login(
    body: LoginRequest = Body(..., description="Login credentials (`email` and `password`)"),
    db: Session = Depends(get_db)
):
    """
    Authenticate user with `email` and `password` fields and return an access token and current user.
    Adjusted for improved reliability and clarity.
    """
    try:
        user = authenticate_user(db, str(body.email), body.password)
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
    db: Session = Depends(get_db),
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
        user = create_user(db, user_create)
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
    db: Session = Depends(get_db),
):
    try:
        change_user_password(
            db,
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
    db: Session = Depends(get_db),
):
    """List all users in the caller's organization. HR managers only."""
    require_hr_manager(current_user)
    users = list_users(db, current_user.organization_id)
    return [UserRead.model_validate(u) for u in users]


class SetActiveBody(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def toggle_user_status(
    user_id: int,
    body: SetActiveBody,
    current_user: Annotated[UserAccount, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Activate or deactivate a user. HR managers only. Cannot deactivate yourself."""
    require_hr_manager(current_user)
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    user = set_user_active(db, user_id, current_user.organization_id, active=body.is_active)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization.",
        )
    return UserRead.model_validate(user)
