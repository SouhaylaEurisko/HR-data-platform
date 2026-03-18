"""
Authentication router — login, signup, and user info endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import get_db
from ..models.user import UserAccount, UserCreate, UserRead
from ..services.auth_service import (
    TokenExpiredError,
    authenticate_user,
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


@router.post("/signup", response_model=dict)
async def signup(
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        user = create_user(db, user_create)
        access_token = create_access_token(subject_user_id=user.id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserRead.model_validate(user),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: Annotated[UserAccount, Depends(get_current_user)],
):
    return UserRead.model_validate(current_user)
