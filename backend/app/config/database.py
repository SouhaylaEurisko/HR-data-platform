"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import config

# Create database engine
engine = create_engine(
    config.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in config.database_url else {}
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
    from ..models import candidate, user  # noqa: F401
    
    # Check if tables exist and have correct schema
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # If candidates table exists, check if it needs migration
    if "candidates" in existing_tables:
        existing_columns = {col["name"] for col in inspector.get_columns("candidates")}
        required_columns = {
            "id", "name", "nationality", "date_of_birth", "position",
            "expected_salary", "years_experience", "current_address",
            "created_at", "updated_at"
        }
        
        # If schema doesn't match, try to add missing columns or drop and recreate
        if not required_columns.issubset(existing_columns):
            missing_columns = required_columns - existing_columns
            print(f"Warning: Database schema mismatch detected. Missing columns: {missing_columns}")
            
            # For PostgreSQL, try to add missing columns
            if "postgresql" in str(engine.url.drivername):
                try:
                    with engine.connect() as conn:
                        if "name" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS name VARCHAR"))
                        if "nationality" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS nationality VARCHAR"))
                        if "date_of_birth" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS date_of_birth DATE"))
                        if "position" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS position VARCHAR"))
                        if "expected_salary" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS expected_salary FLOAT"))
                        if "years_experience" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS years_experience FLOAT"))
                        if "current_address" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS current_address VARCHAR"))
                        if "created_at" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
                        if "updated_at" in missing_columns:
                            conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE"))
                        conn.commit()
                    print("Added missing columns to existing table.")
                except Exception as e:
                    print(f"Failed to add columns: {e}. Dropping and recreating table...")
                    Base.metadata.drop_all(bind=engine)
                    Base.metadata.create_all(bind=engine)
            else:
                # For SQLite or other databases, drop and recreate
                print("Dropping and recreating tables to match schema...")
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
        else:
            # Tables exist and schema matches, just ensure all tables are created
            Base.metadata.create_all(bind=engine)
    else:
        # Tables don't exist, create them
        Base.metadata.create_all(bind=engine)