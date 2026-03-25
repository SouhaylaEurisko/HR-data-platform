"""
Authentication — password hashing, JWT access tokens, and user persistence.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import config
from ..models.user import UserAccount, UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenExpiredError(Exception):
    """JWT signature valid but token past expiry."""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    *,
    subject_user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode a JWT with ``sub`` = user id and standard expiry."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=config.jwt_expire_minutes)
    )
    payload = {"sub": str(subject_user_id), "exp": expire}
    return jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)


def get_user_id_from_token(token: str) -> int:
    """
    Decode bearer token and return user id from ``sub``.
    Raises ``TokenExpiredError`` or ``ValueError`` on failure.
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
        raise ValueError("Invalid token") from exc

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Missing subject")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid subject") from exc


class AccountDeactivatedError(Exception):
    """User account exists but is_active=False."""


def authenticate_user(db: Session, email: str, password: str) -> Optional[UserAccount]:
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        raise AccountDeactivatedError()
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.id == user_id).first()


def create_user(db: Session, user_create: UserCreate) -> UserAccount:
    if db.query(UserAccount).filter(UserAccount.email == user_create.email).first():
        raise ValueError(f"User with email {user_create.email} already exists")

    user = UserAccount(
        organization_id=user_create.organization_id,
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        first_name=user_create.first_name.strip(),
        last_name=user_create.last_name.strip(),
        role=user_create.role or "hr_manager",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, org_id: int) -> list[UserAccount]:
    return (
        db.query(UserAccount)
        .filter(UserAccount.organization_id == org_id)
        .order_by(UserAccount.created_at.desc())
        .all()
    )


def set_user_active(db: Session, user_id: int, org_id: int, *, active: bool) -> Optional[UserAccount]:
    user = (
        db.query(UserAccount)
        .filter(UserAccount.id == user_id, UserAccount.organization_id == org_id)
        .first()
    )
    if user is None:
        return None
    user.is_active = active
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: Session,
    user: UserAccount,
    *,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(user)
