"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, text
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


def _ensure_postgres_candidate_hr_columns() -> None:
    """Add HR-related columns if missing (ORM expects them; older DBs may lack them)."""
    url = (config.database_url or "").lower()
    if "postgresql" not in url:
        return
    stmts = [
        "ALTER TABLE candidate ADD COLUMN IF NOT EXISTS hr_comment TEXT",
        (
            "ALTER TABLE candidate ADD COLUMN IF NOT EXISTS hr_stage_comments "
            "JSONB NOT NULL DEFAULT '{}'::jsonb"
        ),
        "ALTER TABLE candidate ADD COLUMN IF NOT EXISTS application_status VARCHAR(32)",
        (
            "CREATE INDEX IF NOT EXISTS ix_candidate_application_status "
            "ON candidate (application_status)"
        ),
    ]
    normalize_application_status = """
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'candidate'
          AND column_name = 'application_status' AND is_nullable = 'NO'
      ) THEN
        ALTER TABLE candidate ALTER COLUMN application_status DROP DEFAULT;
        ALTER TABLE candidate ALTER COLUMN application_status DROP NOT NULL;
      END IF;
    END $$;
    """
    with engine.begin() as conn:
        for sql in stmts:
            conn.execute(text(sql))
        conn.execute(text(normalize_application_status))


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
        candidate,
        user,
        conversation,
    )
    Base.metadata.create_all(bind=engine)
    _ensure_postgres_candidate_hr_columns()
