"""
Database utilities — safe, read-only query execution for agents.
"""
import re
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..constants import CANDIDATES_SCHEMA, DEFAULT_CANDIDATES_APPLICATIONS_JOIN
from .salary_parser import compute_salary_stats, parse_salary_text

logger = logging.getLogger(__name__)

_LEGACY_CANDIDATE_TABLE_ERROR = (
    'The legacy table "candidate" is not allowed. Use "candidates" with '
    'INNER JOIN applications a ON a.candidate_id = c.id (aliases c / a). '
    'Do not use a CTE named "candidate".'
)

# Legacy flat table name only — allows candidates, candidate_stage_comment, candidate_resume, candidate_id, etc.
_LEGACY_CANDIDATE_TABLE_PATTERNS = (
    # Quoted relation "candidate"
    re.compile(
        r'(?is)(?:\bfrom\b|\bjoin\b)\s+(?:only\s+)?(?:(?:[\w]+\.)?)"candidate"(?=\s|,|\)|;|$)',
    ),
    re.compile(
        r'(?is),\s*(?:(?:[\w]+\.)?)"candidate"(?=\s|,|\)|;|$)',
    ),
    # Unquoted relation candidate (word boundary excludes candidates, candidate_resume, …)
    re.compile(
        r'(?is)(?:\bfrom\b|\bjoin\b)\s+(?:only\s+)?(?:(?:[\w]+\.)?)\bcandidate\b(?![a-z0-9_"])(?=\s|,|\)|;|$)',
    ),
    re.compile(
        r'(?is),\s*(?:(?:[\w]+\.)?)\bcandidate\b(?![a-z0-9_"])(?=\s|,|\)|;|$)',
    ),
)


def _reject_legacy_candidate_table(sql: str) -> None:
    """Disallow reads from the deprecated single-table `candidate` model."""
    for pat in _LEGACY_CANDIDATE_TABLE_PATTERNS:
        if pat.search(sql):
            raise ValueError(_LEGACY_CANDIDATE_TABLE_ERROR)


def execute_safe_query(db: Session, sql: str) -> List[Dict[str, Any]]:
    """
    Execute a read-only SQL query and return rows as list of dicts.
    Only SELECT statements allowed. Results capped at 50 rows.
    """
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    _reject_legacy_candidate_table(cleaned)

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
    upper = cleaned.upper()
    for kw in forbidden:
        if f" {kw} " in f" {upper} " or upper.startswith(f"{kw} "):
            raise ValueError(f"Forbidden SQL keyword detected: {kw}")

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
    cleaned = sql.strip().rstrip(";").strip()
    upper = cleaned.upper()
    from_idx = upper.find("FROM")
    if from_idx == -1:
        return DEFAULT_CANDIDATES_APPLICATIONS_JOIN
    tail = cleaned[from_idx:]
    tail = re.sub(
        r"\s+(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\s+.*$",
        "", tail, flags=re.IGNORECASE | re.DOTALL,
    )
    tail = tail.replace(";", "")
    return tail.strip()


def fetch_salary_stats_for_query(
    db: Session,
    original_sql: str,
) -> Optional[Dict[str, Any]]:
    """
    For salary aggregation queries, fetch raw current_salary values
    from the same filtered set and compute correct stats in Python.
    """
    if "current_salary" not in original_sql.lower():
        return None

    from_clause = _extract_where_clause(original_sql)

    if "WHERE" in from_clause.upper():
        salary_sql = (
            f"SELECT current_salary {from_clause} "
            f"AND current_salary IS NOT NULL "
            f"LIMIT 10000"
        )
    else:
        salary_sql = (
            f"SELECT current_salary {from_clause} "
            f"WHERE current_salary IS NOT NULL "
            f"LIMIT 10000"
        )

    try:
        rows = execute_safe_query(db, salary_sql)
    except (ValueError, RuntimeError) as exc:
        logger.warning(f"Salary correction query failed: {exc}")
        return None

    if not rows:
        return None

    values = [float(r["current_salary"]) for r in rows if r.get("current_salary") is not None]
    if not values:
        return None

    return {
        "count": len(values),
        "min_salary": min(values),
        "max_salary": max(values),
        "avg_salary": round(sum(values) / len(values), 2),
    }


# ── Experience sanity correction ─────────────────────────────────────────────

_MAX_REASONABLE_EXPERIENCE = 50


def fetch_experience_stats_for_query(
    db: Session,
    original_sql: str,
) -> Optional[Dict[str, Any]]:
    if "years_of_experience" not in original_sql.lower():
        return None

    from_clause = _extract_where_clause(original_sql)

    if "WHERE" in from_clause.upper():
        exp_sql = (
            f"SELECT years_of_experience {from_clause} "
            f"AND years_of_experience IS NOT NULL "
            f"AND years_of_experience <= {_MAX_REASONABLE_EXPERIENCE} "
            f"LIMIT 10000"
        )
    else:
        exp_sql = (
            f"SELECT years_of_experience {from_clause} "
            f"WHERE years_of_experience IS NOT NULL "
            f"AND years_of_experience <= {_MAX_REASONABLE_EXPERIENCE} "
            f"LIMIT 10000"
        )

    try:
        rows = execute_safe_query(db, exp_sql)
    except (ValueError, RuntimeError) as exc:
        logger.warning(f"Experience correction query failed: {exc}")
        return None

    if not rows:
        return None

    values = [float(r["years_of_experience"]) for r in rows if r.get("years_of_experience") is not None]
    if not values:
        return None

    return {
        "count": len(values),
        "min_experience": min(values),
        "max_experience": max(values),
        "avg_experience": round(sum(values) / len(values), 2),
    }


# ── Salary-aware filter execution ────────────────────────────────────────────

# Match current_salary as a filter column, excluding alias.c2 / t2 style (digit before dot → c2.current_salary).
# Also exclude bare matches that are really "c2.current_salary" via (?<!\d)\. only matching .current_salary when the dot is not after a digit.
_CS_COL = r"(?:(?<!\d)\.current_salary|(?:^|[^\w.])(?:c\.|a\.)?current_salary)"

_SALARY_SIMPLE_RE = re.compile(
    _CS_COL + r"""\s*(=|>=|<=|>|<|!=)\s*([\d\.]+)""",
    re.IGNORECASE,
)

_SALARY_BETWEEN_RE = re.compile(
    _CS_COL + r"""\s+BETWEEN\s+([\d\.]+)\s+AND\s+([\d\.]+)""",
    re.IGNORECASE,
)

# Detect cohort max/min: c.current_salary = (SELECT MAX( ... current_salary ...) ... ) — never strip these in Python.
_SALARY_COHORT_SUBQUERY_RE = re.compile(
    _CS_COL + r"""\s*=\s*\(\s*SELECT\s+(?:MAX|MIN)\s*\(""",
    re.IGNORECASE,
)

_SALARY_SUBQUERY_RE = _SALARY_COHORT_SUBQUERY_RE

_SALARY_IS_NOT_NULL_RE = re.compile(
    _CS_COL + r"\s+IS\s+NOT\s+NULL",
    re.IGNORECASE,
)

# Only strip simple numeric comparisons; never strip "= (SELECT ...)" (regex cannot safely span nested parens).
_SALARY_CONDITION_RE = re.compile(
    r"""(?:AND\s+)?"""
    + _CS_COL
    + r"""\s*"""
    r"""(?:"""
    r"""(?:=|>=|<=|>|<|!=)\s*[\d\.]+"""
    r"""|"""
    r"""BETWEEN\s+[\d\.]+\s+AND\s+[\d\.]+"""
    r"""|"""
    r"""IS\s+NOT\s+NULL"""
    r""")"""
    r"""(?:\s+AND)?""",
    re.IGNORECASE,
)


def _has_salary_filter(sql: str) -> bool:
    upper = sql.upper()
    where_idx = upper.find("WHERE")
    if where_idx == -1:
        return False
    where_part = sql[where_idx:]
    return bool(
        _SALARY_SIMPLE_RE.search(where_part)
        or _SALARY_BETWEEN_RE.search(where_part)
        or _SALARY_SUBQUERY_RE.search(where_part)
        or _SALARY_IS_NOT_NULL_RE.search(where_part)
    )


def _build_salary_matcher(
    sql: str,
) -> Optional[Callable[[Optional[Tuple[float, float]]], bool]]:
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

    if _SALARY_IS_NOT_NULL_RE.search(sql):
        return lambda r: r is not None

    return None


def _remove_salary_conditions(sql: str) -> str:
    upper = sql.upper()
    where_idx = upper.find("WHERE")
    if where_idx == -1:
        return sql
    before = sql[:where_idx]
    after = sql[where_idx:]
    cleaned = _SALARY_CONDITION_RE.sub("", after)
    cleaned = re.sub(r"WHERE\s+(?=ORDER|GROUP|HAVING|LIMIT|$)", "WHERE 1=1 ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"AND\s+AND", "AND", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"WHERE\s+AND\s+", "WHERE ", cleaned, flags=re.IGNORECASE)
    return before + cleaned


def _extract_limit(sql: str) -> Optional[int]:
    match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _replace_limit(sql: str, new_limit: int) -> str:
    return re.sub(r"LIMIT\s+\d+", f"LIMIT {new_limit}", sql, flags=re.IGNORECASE)


_SALARY_BROAD_LIMIT = 500


def execute_salary_aware_query(
    db: Session,
    sql: str,
) -> Tuple[List[Dict[str, Any]], bool]:
    if not _has_salary_filter(sql):
        return execute_safe_query(db, sql), False

    # Subquery max/min cohort queries must run verbatim — stripping salary breaks nested parentheses.
    if _SALARY_COHORT_SUBQUERY_RE.search(sql):
        return execute_safe_query(db, sql), False

    matcher = _build_salary_matcher(sql)
    if matcher is None:
        return execute_safe_query(db, sql), False

    original_limit = _extract_limit(sql) or 20

    broader_sql = _remove_salary_conditions(sql)
    if _extract_limit(broader_sql) is not None:
        broader_sql = _replace_limit(broader_sql, _SALARY_BROAD_LIMIT)
    if "LIMIT" not in broader_sql.upper():
        broader_sql = broader_sql.rstrip().rstrip(";") + f" LIMIT {_SALARY_BROAD_LIMIT}"

    rows = execute_safe_query(db, broader_sql)

    filtered = []
    for row in rows:
        salary_val = row.get("current_salary")
        if salary_val is not None:
            val = float(salary_val)
            parsed = (val, val)
        else:
            parsed = None
        if matcher(parsed):
            filtered.append(row)

    filtered = filtered[:original_limit]
    return filtered, True
