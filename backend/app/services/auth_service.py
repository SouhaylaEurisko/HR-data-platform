"""
Authentication service — password hashing, JWT token generation, and user management.
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import config
from ..models.user import UserAccount, UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.jwt_secret_key, algorithm=config.jwt_algorithm)


def authenticate_user(db: Session, email: str, password: str) -> Optional[UserAccount]:
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_email(db: Session, email: str) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.id == user_id).first()


def create_user(db: Session, user_create: UserCreate) -> UserAccount:
    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise ValueError(f"User with email {user_create.email} already exists")

    hashed_password = get_password_hash(user_create.password)
    user = UserAccount(
        organization_id=user_create.organization_id,
        email=user_create.email,
        hashed_password=hashed_password,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        role=user_create.role or "hr_viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
