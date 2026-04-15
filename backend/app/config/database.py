"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import config

engine = create_engine(
    config.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if "sqlite" in config.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined by SQLAlchemy models."""
    from ..models import (  # noqa: F401
        organization,
        lookup,
        custom_field,
        import_session,
        candidates,
        applications,
        candidate_stage_comment,
        candidate_resume,
        user,
        conversation,
    )
    Base.metadata.create_all(bind=engine)

