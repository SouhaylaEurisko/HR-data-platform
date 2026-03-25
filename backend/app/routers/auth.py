"""
Authentication router — login, user provisioning (HR manager), password change, and /me.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.user import (
    AdminUserCreate,
    ChangePasswordRequest,
    UserAccount,
    UserCreate,
    UserRead,
)
from ..services.auth_service import (
    TokenExpiredError,
    authenticate_user,
    change_user_password,
    create_access_token,
    create_user,
    get_user_by_id,
    get_user_id_from_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> UserAccount:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
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
    return user


HR_MANAGER_ROLE = "hr_manager"


def require_hr_manager(current_user: UserAccount) -> None:
    if current_user.role != HR_MANAGER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR managers can perform this action.",
        )


@router.post("/login", response_model=dict)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject_user_id=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user),
    }


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
