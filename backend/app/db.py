from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./hr_data.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(column_name: str, column_type: str, create_index: bool = False):
    """
    Helper function to add a column to candidates table if it doesn't exist.
    """
    try:
        inspector = inspect(engine)
        if 'candidates' not in inspector.get_table_names():
            return
        
        columns = [col['name'] for col in inspector.get_columns('candidates')]
        
        if column_name not in columns:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {column_name} {column_type}"))
                if create_index:
                    try:
                        conn.execute(text(f"CREATE INDEX ix_candidates_{column_name} ON candidates({column_name})"))
                    except Exception:
                        pass
                conn.commit()
                print(f"Migration: Added {column_name} column to candidates table")
    except Exception as e:
        print(f"Migration note for {column_name}: {e}")


def migrate_add_source_sheet_column():
    """Migration: Add source_sheet column to candidates table if it doesn't exist."""
    _add_column_if_missing("source_sheet", "VARCHAR(255)", create_index=True)


def migrate_add_source_table_index_column():
    """Migration: Add source_table_index column to candidates table if it doesn't exist."""
    _add_column_if_missing("source_table_index", "INTEGER")


def migrate_add_expected_salary_text_column():
    """Migration: Add expected_salary_text column to candidates table if it doesn't exist."""
    _add_column_if_missing("expected_salary_text", "VARCHAR(255)")

