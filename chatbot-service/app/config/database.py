"""
Database configuration and session management for chatbot service.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import config

# Create database engine
# For PostgreSQL, use connection pooling
if "postgresql" in config.database_url or "postgres" in config.database_url:
    engine = create_engine(
        config.database_url,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
        echo=False,          # Set to True for SQL query logging
    )
else:
    # For SQLite (fallback)
    engine = create_engine(
        config.database_url,
        connect_args={"check_same_thread": False}
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and closes it after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called on application startup.
    """
    # Import all models here so they're registered with Base
    from ..models import conversation  # noqa: F401
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
