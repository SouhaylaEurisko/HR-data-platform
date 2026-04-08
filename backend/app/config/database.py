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
        candidate,
        candidate_stage_comment,
        candidate_resume,
        user,
        conversation,
    )
    Base.metadata.create_all(bind=engine)
    _ensure_candidate_stage_comment_fk()


def _ensure_candidate_stage_comment_fk() -> None:
    """
    Keep candidate_stage_comment.candidate_id linked to new candidates.id.
    This is a lightweight compatibility fix for existing DBs without migrations.
    """
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "candidate_stage_comment" not in tables or "candidates" not in tables:
            return

        fks = inspector.get_foreign_keys("candidate_stage_comment")
        target_ok = any(
            fk.get("constrained_columns") == ["candidate_id"]
            and fk.get("referred_table") == "candidates"
            for fk in fks
        )
        if target_ok:
            return

        for fk in fks:
            if fk.get("constrained_columns") == ["candidate_id"] and fk.get("name"):
                conn.execute(
                    text(f'ALTER TABLE candidate_stage_comment DROP CONSTRAINT "{fk["name"]}"')
                )

        conn.execute(
            text(
                "ALTER TABLE candidate_stage_comment "
                "ADD CONSTRAINT candidate_stage_comment_candidate_id_fkey "
                "FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE"
            )
        )
