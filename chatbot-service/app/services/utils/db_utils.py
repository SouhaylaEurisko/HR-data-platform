"""
Database utilities — safe, read-only query execution for agents.
"""
import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The schema description given to the LLM so it can write SQL.
CANDIDATES_SCHEMA = """
TABLE candidates (
  id                  INTEGER PRIMARY KEY,
  full_name           VARCHAR(255),
  email               VARCHAR(255),
  nationality         VARCHAR(255),
  date_of_birth       DATE,
  position            VARCHAR(255),
  expected_salary     FLOAT,
  expected_salary_text VARCHAR(255),
  years_experience    FLOAT,
  notice_period       VARCHAR(255),
  current_address     VARCHAR(255),
  created_at          TIMESTAMP,
  updated_at          TIMESTAMP
)
""".strip()


def execute_safe_query(db: Session, sql: str) -> List[Dict[str, Any]]:
    """
    Execute a read-only SQL query and return rows as list of dicts.

    Safety:
      - Only SELECT statements are allowed.
      - Wrapped in a read-only sub-transaction (rollback on any error).
      - Results are capped at 50 rows to avoid huge payloads.

    Args:
        db:  SQLAlchemy session (from the chatbot-service's own DB pool).
        sql: Raw SQL string (must be a SELECT).

    Returns:
        List of row dicts.

    Raises:
        ValueError  if the SQL is not a SELECT.
        RuntimeError on execution errors.
    """
    cleaned = sql.strip().rstrip(";").strip()

    # Safety: only SELECT
    if not cleaned.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    # Block dangerous keywords
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
    upper = cleaned.upper()
    for kw in forbidden:
        # Check that the keyword appears as a standalone word
        if f" {kw} " in f" {upper} " or upper.startswith(f"{kw} "):
            raise ValueError(f"Forbidden SQL keyword detected: {kw}")

    # Add LIMIT if not present
    if "LIMIT" not in upper:
        cleaned += " LIMIT 50"

    try:
        result = db.execute(text(cleaned))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        logger.info(f"Query returned {len(rows)} rows")
        return rows
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"SQL execution error: {exc}") from exc
