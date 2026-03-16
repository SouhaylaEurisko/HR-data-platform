"""
Database utilities — safe, read-only query execution for agents.
"""
import re
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from .salary_parser import compute_salary_stats, parse_salary_text

logger = logging.getLogger(__name__)

# The schema description given to the LLM so it can write SQL.
#
# NOTE: ``expected_salary`` (FLOAT) contains unreliable values because
# free-text salary strings like "1500$- 1800/2500" are naively parsed
# into a single number.  For any salary-related aggregation the agents
# must use the Python-based salary correction step instead.
CANDIDATES_SCHEMA = """
TABLE candidates (
  id                  INTEGER PRIMARY KEY,
  full_name           VARCHAR(255),
  email               VARCHAR(255),
  nationality         VARCHAR(255),
  date_of_birth       DATE,
  position            VARCHAR(255),
  expected_salary     FLOAT,              -- WARNING: unreliable parsed value
  expected_salary_text VARCHAR(255),       -- raw salary text (source of truth)
  years_experience    FLOAT,              -- WARNING: may contain corrupt values (use <= 50 bound)
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


# ── Salary correction helpers ────────────────────────────────────────────────

def _extract_where_clause(sql: str) -> str:
    """
    Extract the FROM … WHERE … portion of a SQL statement, stripping
    GROUP BY / ORDER BY / LIMIT / HAVING tails.

    Returns the clause starting at ``FROM`` so callers can prepend their
    own SELECT list.
    """
    # Strip trailing semicolons and whitespace first
    cleaned = sql.strip().rstrip(";").strip()

    upper = cleaned.upper()
    from_idx = upper.find("FROM")
    if from_idx == -1:
        return "FROM candidates"

    tail = cleaned[from_idx:]

    # Remove everything after GROUP BY / ORDER BY / HAVING / LIMIT
    tail = re.sub(
        r"\s+(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\s+.*$",
        "",
        tail,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Remove any stray semicolons that may remain
    tail = tail.replace(";", "")
    return tail.strip()


def fetch_salary_stats_for_query(
    db: Session,
    original_sql: str,
) -> Optional[Dict[str, Any]]:
    """
    Given an aggregation SQL that references ``expected_salary``, run a
    companion query that fetches the raw ``expected_salary_text`` values
    from the same filtered set, parse them in Python, and return correct
    salary statistics.

    Returns ``None`` when the original SQL does not involve salary or when
    no parseable salary texts are found.
    """
    if "expected_salary" not in original_sql.lower():
        return None

    from_clause = _extract_where_clause(original_sql)

    # Build a query to fetch salary texts with the same WHERE filters.
    # Use a high LIMIT — we need ALL matching rows for correct stats.
    if "WHERE" in from_clause.upper():
        salary_sql = (
            f"SELECT expected_salary_text {from_clause} "
            f"AND expected_salary_text IS NOT NULL "
            f"LIMIT 10000"
        )
    else:
        salary_sql = (
            f"SELECT expected_salary_text {from_clause} "
            f"WHERE expected_salary_text IS NOT NULL "
            f"LIMIT 10000"
        )

    try:
        rows = execute_safe_query(db, salary_sql)
    except (ValueError, RuntimeError) as exc:
        logger.warning(f"Salary correction query failed: {exc}")
        return None

    if not rows:
        return None

    texts = [r["expected_salary_text"] for r in rows if r.get("expected_salary_text")]
    if not texts:
        return None

    stats = compute_salary_stats(texts)
    return stats if stats else None


# ── Experience sanity correction ─────────────────────────────────────────────

# Any years_experience above this is considered corrupt data.
_MAX_REASONABLE_EXPERIENCE = 50


def fetch_experience_stats_for_query(
    db: Session,
    original_sql: str,
) -> Optional[Dict[str, Any]]:
    """
    Given an aggregation SQL that references ``years_experience``, run a
    companion query that fetches only sane experience values (≤ 50) from
    the same filtered set and compute correct statistics in Python.

    Returns ``None`` when the SQL does not involve experience or when no
    valid values are found.
    """
    if "years_experience" not in original_sql.lower():
        return None

    from_clause = _extract_where_clause(original_sql)

    # Build a query fetching only sane experience values.
    # Use a high LIMIT — we need ALL matching rows for correct stats.
    if "WHERE" in from_clause.upper():
        exp_sql = (
            f"SELECT years_experience {from_clause} "
            f"AND years_experience IS NOT NULL "
            f"AND years_experience <= {_MAX_REASONABLE_EXPERIENCE} "
            f"LIMIT 10000"
        )
    else:
        exp_sql = (
            f"SELECT years_experience {from_clause} "
            f"WHERE years_experience IS NOT NULL "
            f"AND years_experience <= {_MAX_REASONABLE_EXPERIENCE} "
            f"LIMIT 10000"
        )

    try:
        rows = execute_safe_query(db, exp_sql)
    except (ValueError, RuntimeError) as exc:
        logger.warning(f"Experience correction query failed: {exc}")
        return None

    if not rows:
        return None

    values = [float(r["years_experience"]) for r in rows if r.get("years_experience") is not None]
    if not values:
        return None

    return {
        "count": len(values),
        "min_experience": min(values),
        "max_experience": max(values),
        "avg_experience": round(sum(values) / len(values), 2),
    }


# ── Salary-aware filter execution ────────────────────────────────────────────

# Patterns for salary conditions in WHERE clauses.
# Handles:  expected_salary = 2500
#           expected_salary >= 2000
#           expected_salary BETWEEN 1000 AND 3000
#           expected_salary = (SELECT MAX(expected_salary) ...)
_SALARY_SIMPLE_RE = re.compile(
    r"""expected_salary\s*(=|>=|<=|>|<|!=)\s*([\d\.]+)""",
    re.IGNORECASE,
)

_SALARY_BETWEEN_RE = re.compile(
    r"""expected_salary\s+BETWEEN\s+([\d\.]+)\s+AND\s+([\d\.]+)""",
    re.IGNORECASE,
)

_SALARY_SUBQUERY_RE = re.compile(
    r"""expected_salary\s*(=|>=|<=|>|<)\s*\(\s*SELECT\s+(?:MAX|MIN)\s*\(\s*expected_salary\s*\)\s+FROM\s+candidates[^)]*\)""",
    re.IGNORECASE,
)

# Pattern to strip a salary condition (and surrounding AND/OR) from WHERE.
# This handles the condition preceded/followed by AND.
_SALARY_CONDITION_RE = re.compile(
    r"""(?:AND\s+)?"""                                 # optional leading AND
    r"""expected_salary\s*"""
    r"""(?:"""
    r"""(?:=|>=|<=|>|<|!=)\s*"""
    r"""(?:\(\s*SELECT[^)]+\)|[\d\.]+)"""              # subquery or number
    r"""|"""
    r"""BETWEEN\s+[\d\.]+\s+AND\s+[\d\.]+"""           # BETWEEN
    r"""|"""
    r"""IS\s+NOT\s+NULL"""                              # IS NOT NULL
    r""")"""
    r"""(?:\s+AND)?""",                                 # optional trailing AND
    re.IGNORECASE,
)


def _has_salary_filter(sql: str) -> bool:
    """Return True if the SQL WHERE clause filters on ``expected_salary``."""
    upper = sql.upper()
    where_idx = upper.find("WHERE")
    if where_idx == -1:
        return False
    where_part = sql[where_idx:]
    return bool(
        _SALARY_SIMPLE_RE.search(where_part)
        or _SALARY_BETWEEN_RE.search(where_part)
        or _SALARY_SUBQUERY_RE.search(where_part)
    )


def _build_salary_matcher(
    sql: str,
) -> Optional[Callable[[Optional[Tuple[float, float]]], bool]]:
    """
    Parse the salary condition from the SQL and return a callable that
    checks whether a ``(min_salary, max_salary)`` tuple satisfies it.

    For ``= X``:  X falls within [min, max]  (i.e. the range includes X)
    For ``>= X``: max >= X
    For ``> X``:  max > X
    For ``<= X``: min <= X
    For ``< X``:  min < X
    For ``BETWEEN lo AND hi``:  ranges overlap  (max >= lo AND min <= hi)
    """
    between = _SALARY_BETWEEN_RE.search(sql)
    if between:
        lo, hi = float(between.group(1)), float(between.group(2))
        return lambda r: r is not None and r[1] >= lo and r[0] <= hi

    simple = _SALARY_SIMPLE_RE.search(sql)
    if simple:
        op, val = simple.group(1), float(simple.group(2))
        matchers = {
            "=":  lambda r: r is not None and r[0] <= val <= r[1],
            ">=": lambda r: r is not None and r[1] >= val,
            ">":  lambda r: r is not None and r[1] > val,
            "<=": lambda r: r is not None and r[0] <= val,
            "<":  lambda r: r is not None and r[0] < val,
            "!=": lambda r: r is not None and not (r[0] <= val <= r[1]),
        }
        return matchers.get(op)

    return None


def _remove_salary_conditions(sql: str) -> str:
    """
    Return a copy of *sql* with ``expected_salary`` conditions stripped
    from the WHERE clause.  If the WHERE clause becomes empty, it is
    replaced with ``WHERE 1=1``.
    """
    upper = sql.upper()
    where_idx = upper.find("WHERE")
    if where_idx == -1:
        return sql

    before = sql[:where_idx]
    after = sql[where_idx:]

    # Remove salary conditions
    cleaned = _SALARY_CONDITION_RE.sub("", after)

    # Clean up leftover whitespace / dangling AND / OR
    # Remove "WHERE" followed only by whitespace and ORDER/GROUP/LIMIT/end
    cleaned = re.sub(r"WHERE\s+(?=ORDER|GROUP|HAVING|LIMIT|$)", "WHERE 1=1 ", cleaned, flags=re.IGNORECASE)
    # Remove double ANDs
    cleaned = re.sub(r"AND\s+AND", "AND", cleaned, flags=re.IGNORECASE)
    # Remove leading AND right after WHERE
    cleaned = re.sub(r"WHERE\s+AND\s+", "WHERE ", cleaned, flags=re.IGNORECASE)

    return before + cleaned


def _extract_limit(sql: str) -> Optional[int]:
    """Extract the LIMIT value from the SQL, or None if absent."""
    match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _replace_limit(sql: str, new_limit: int) -> str:
    """Replace the LIMIT clause in the SQL with a new value."""
    return re.sub(r"LIMIT\s+\d+", f"LIMIT {new_limit}", sql, flags=re.IGNORECASE)


# How many rows to fetch in the broader query before post-filtering.
# Must be large enough that after filtering we still have enough results.
_SALARY_BROAD_LIMIT = 500


def execute_salary_aware_query(
    db: Session,
    sql: str,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Execute a filter query with salary-aware post-processing.

    If the SQL filters on ``expected_salary``, this function:

    1. Runs a *broader* query with the salary condition removed and a
       much higher LIMIT (so we don't miss matching rows).
    2. Parses ``expected_salary_text`` for every returned row.
    3. Applies the salary condition in Python against the parsed range.
    4. Trims the result to the original LIMIT.

    Returns:
        A tuple of ``(rows, was_corrected)`` where *was_corrected* is
        ``True`` when salary post-filtering was applied.
    """
    if not _has_salary_filter(sql):
        return execute_safe_query(db, sql), False

    matcher = _build_salary_matcher(sql)
    if matcher is None:
        # Subquery pattern (e.g. = (SELECT MAX(...))); can't post-filter
        # meaningfully — fall back to normal execution.
        return execute_safe_query(db, sql), False

    # Remember the original LIMIT so we can re-apply after filtering.
    original_limit = _extract_limit(sql) or 20

    # Build broader SQL: no salary condition + high limit
    broader_sql = _remove_salary_conditions(sql)
    if _extract_limit(broader_sql) is not None:
        broader_sql = _replace_limit(broader_sql, _SALARY_BROAD_LIMIT)
    # execute_safe_query will add LIMIT 50 if none present — we need more,
    # so ensure there's always an explicit higher limit.
    if "LIMIT" not in broader_sql.upper():
        broader_sql = broader_sql.rstrip().rstrip(";") + f" LIMIT {_SALARY_BROAD_LIMIT}"

    logger.info(f"Salary-aware query — broader SQL: {broader_sql}")

    rows = execute_safe_query(db, broader_sql)

    filtered = []
    for row in rows:
        salary_text = row.get("expected_salary_text")
        parsed = parse_salary_text(salary_text)
        if matcher(parsed):
            filtered.append(row)

    # Apply original LIMIT
    filtered = filtered[:original_limit]

    logger.info(
        f"Salary post-filter: {len(rows)} broad → {len(filtered)} matched "
        f"(limit {original_limit})"
    )
    return filtered, True
