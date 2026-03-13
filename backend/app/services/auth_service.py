"""
Authentication service — password hashing, JWT token generation, and user management.
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import config
from ..models.user import User, UserCreate, UserRead

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    """Create a new user."""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise ValueError(f"User with email {user_create.email} already exists")
    
    hashed_password = get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
