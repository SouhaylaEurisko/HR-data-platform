"""Build UserAccount from create schemas (password hashing stays in auth_service)."""

from ..constants import Auth
from ..models.user import UserAccount
from ..schemas.user import AdminUserCreate, UserCreate


def user_account_from_create(user_create: UserCreate, *, hashed_password: str) -> UserAccount:
    return UserAccount(
        organization_id=user_create.organization_id,
        email=user_create.email,
        hashed_password=hashed_password,
        first_name=user_create.first_name.strip(),
        last_name=user_create.last_name.strip(),
        role=user_create.role or Auth.HR_MANAGER_ROLE,
        is_active=True,
    )


def user_create_from_admin(body: AdminUserCreate, *, organization_id: int) -> UserCreate:
    """Map HR-manager invite body to internal UserCreate (caller supplies org from current user)."""
    return UserCreate(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        organization_id=organization_id,
        role=body.role,
    )
