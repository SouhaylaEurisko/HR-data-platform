"""
Authentication router — login, signup, and user info endpoints.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import get_db, config
from ..models.user import User, UserCreate, UserRead
from ..services.auth_service import (
    authenticate_user,
    create_user,
    create_access_token,
    get_user_by_id,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    from jose import JWTError, jwt
    import logging
    
    logger = logging.getLogger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Log token presence (first 20 chars only for security)
    logger.debug(f"Validating token: {token[:20]}..." if token and len(token) > 20 else "Token received")
    
    try:
        payload = jwt.decode(
            token, config.jwt_secret_key, algorithms=[config.jwt_algorithm]
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        user_id = int(user_id_str)
        logger.debug(f"Token validated for user ID: {user_id}")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        # JWTError covers all JWT-related errors (invalid token, wrong algorithm, etc.)
        logger.warning(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except (ValueError, TypeError) as e:
        logger.warning(f"Token validation error: {str(e)}")
        raise credentials_exception
    
    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        logger.warning(f"User with ID {user_id} not found in database")
        raise credentials_exception
    logger.debug(f"User authenticated: {user.email} (ID: {user.id})")
    return user


@router.post("/login", response_model=dict)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """
    Login endpoint - accepts OAuth2PasswordRequestForm (username=email, password).
    Returns JWT access token.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 'sub' claim must be a string
    access_token = create_access_token(data={"sub": str(user.id)})
    
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
    """
    Signup endpoint - create a new user account.
    """
    try:
        user = create_user(db, user_create)
        # JWT 'sub' claim must be a string
        access_token = create_access_token(data={"sub": str(user.id)})
        
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
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get current user information from JWT token.
    """
    return UserRead.model_validate(current_user)
