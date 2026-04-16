"""
Authentication — password hashing, JWT access tokens, and user persistence.
DB access lives in repository.auth_repository.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import config
from ..exceptions import AccountDeactivatedError, BusinessRuleError, ConflictError, InvalidTokenError, TokenExpiredError
from ..models.user import UserAccount
from ..factories.user_factory import user_account_from_create
from ..repository.auth_repository import AuthRepositoryProtocol
from ..schemas.user import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    *,
    subject_user_id: int,
    email: Optional[str] = None,
    organization_id: Optional[int] = None,
    role: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> str:
    """Encode a JWT with subject and basic user claims."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expire_minutes)

    payload = {
        "sub": str(subject_user_id),
        "exp": expire,
    }
    if email:
        payload["email"] = email
    if organization_id is not None:
        payload["organization_id"] = organization_id
    if role:
        payload["role"] = role
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    return jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)


def get_user_id_from_token(token: str) -> int:
    """
    Decode bearer token and return user id from ``sub``.
    Raises ``TokenExpiredError`` or ``InvalidTokenError`` on failure.
    """
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError from exc
    except JWTError as exc:
        raise InvalidTokenError("Could not validate credentials") from exc

    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError("Could not validate credentials")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("Could not validate credentials") from exc


class AuthServiceProtocol(Protocol):
    def authenticate_user(self, email: str, password: str) -> Optional[UserAccount]: ...
    def get_user_by_id(self, user_id: int) -> Optional[UserAccount]: ...
    def create_user(self, user_create: UserCreate) -> UserAccount: ...
    def list_users(self, org_id: int) -> list[UserAccount]: ...
    def set_user_active(self, user_id: int, org_id: int, *, active: bool) -> Optional[UserAccount]: ...
    def change_user_password(
        self,
        user: UserAccount,
        *,
        current_password: str,
        new_password: str,
    ) -> None: ...


class AuthService:
    def __init__(self, user_repo: AuthRepositoryProtocol) -> None:
        self._user_repo = user_repo

    def authenticate_user(self, email: str, password: str) -> Optional[UserAccount]:
        user = self._user_repo.get_user_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            raise AccountDeactivatedError()
        return user

    def get_user_by_id(self, user_id: int) -> Optional[UserAccount]:
        return self._user_repo.get_user_by_id(user_id)

    def create_user(self, user_create: UserCreate) -> UserAccount:
        if self._user_repo.email_taken(user_create.email):
            raise ConflictError(f"User with email {user_create.email} already exists")

        new_user = user_account_from_create(
            user_create,
            hashed_password=get_password_hash(user_create.password),
        )
        return self._user_repo.insert_user(new_user)

    def list_users(self, org_id: int) -> list[UserAccount]:
        return self._user_repo.list_users_by_org(org_id)

    def set_user_active(self, user_id: int, org_id: int, *, active: bool) -> Optional[UserAccount]:
        return self._user_repo.set_user_active_in_org(user_id, org_id, active=active)

    def change_user_password(
        self,
        user: UserAccount,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise BusinessRuleError("Current password is incorrect")
        self._user_repo.update_user_hashed_password(user, get_password_hash(new_password))

