"""
Authentication dependencies shared across routers.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..constants import Auth
from ..models.user import UserAccount
from ..services.auth_service import (
    AuthServiceProtocol,
    TokenExpiredError,
    get_user_id_from_token,
)
from .services import get_auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def _raise_credentials_exception() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> UserAccount:
    token = credentials.credentials if credentials is not None else None
    if token is None:
        _raise_credentials_exception()

    try:
        user_id = get_user_id_from_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except ValueError:
        _raise_credentials_exception()

    user = auth_service.get_user_by_id(user_id)
    if user is None:
        _raise_credentials_exception()
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
