"""User account persistence and queries."""

from typing import Optional

from sqlalchemy.orm import Session

from ..models.user import UserAccount


def get_user_by_email(db: Session, email: str) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.id == user_id).first()


def email_taken(db: Session, email: str) -> bool:
    return db.query(UserAccount).filter(UserAccount.email == email).first() is not None


def insert_user(db: Session, user: UserAccount) -> UserAccount:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users_by_org(db: Session, org_id: int) -> list[UserAccount]:
    return (
        db.query(UserAccount)
        .filter(UserAccount.organization_id == org_id)
        .order_by(UserAccount.created_at.desc())
        .all()
    )


def get_user_in_org(db: Session, user_id: int, org_id: int) -> Optional[UserAccount]:
    return (
        db.query(UserAccount)
        .filter(UserAccount.id == user_id, UserAccount.organization_id == org_id)
        .first()
    )


def set_user_active_in_org(db: Session, user_id: int, org_id: int, *, active: bool) -> Optional[UserAccount]:
    user = get_user_in_org(db, user_id, org_id)
    if user is None:
        return None
    user.is_active = active
    db.commit()
    db.refresh(user)
    return user


def update_user_hashed_password(db: Session, user: UserAccount, hashed_password: str) -> None:
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
