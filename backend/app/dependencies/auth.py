"""
Authentication dependencies shared across routers.
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..constants import Auth
from ..exceptions import (
    AccountDeactivatedError,
    CredentialsRequiredError,
    InsufficientPermissionsError,
    InvalidTokenError,
)
from ..models.user import UserAccount
from ..services.auth_service import AuthServiceProtocol, get_user_id_from_token
from .services import get_auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> UserAccount:
    token = credentials.credentials if credentials is not None else None
    if token is None:
        raise CredentialsRequiredError()

    user_id = get_user_id_from_token(token)

    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise InvalidTokenError("Could not validate credentials")
    if not user.is_active:
        raise AccountDeactivatedError()
    return user


def require_hr_manager(current_user: UserAccount) -> None:
    if current_user.role != Auth.HR_MANAGER_ROLE:
        raise InsufficientPermissionsError()
