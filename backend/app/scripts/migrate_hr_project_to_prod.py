"""
Migrate data from `hr_project_database` (legacy schema) to
`hr_project_database_prod` (new split schema).

Usage:
    cd hr_platform/backend
    python -m app.scripts.migrate_hr_project_to_prod

Optional overrides:
    python -m app.scripts.migrate_hr_project_to_prod \
      --source-url "postgresql+psycopg2://user:pass@localhost:5432/hr_project_database" \
      --target-url "postgresql+psycopg2://user:pass@localhost:5432/hr_project_database_prod" \
      --truncate-target
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


DEFAULT_DB_USER = os.getenv("MIGRATION_DB_USER", "ai-team")
DEFAULT_DB_PASSWORD = os.getenv("MIGRATION_DB_PASSWORD", "ai-team_123*")
DEFAULT_DB_HOST = os.getenv("MIGRATION_DB_HOST", "localhost")
DEFAULT_DB_PORT = os.getenv("MIGRATION_DB_PORT", "5432")

DEFAULT_SOURCE_URL = os.getenv(
    "SOURCE_DATABASE_URL",
    f"postgresql+psycopg2://{DEFAULT_DB_USER}:{DEFAULT_DB_PASSWORD}@{DEFAULT_DB_HOST}:{DEFAULT_DB_PORT}/hr_project_database",
)
DEFAULT_TARGET_URL = os.getenv(
    "TARGET_DATABASE_URL",
    f"postgresql+psycopg2://{DEFAULT_DB_USER}:{DEFAULT_DB_PASSWORD}@{DEFAULT_DB_HOST}:{DEFAULT_DB_PORT}/hr_project_database_prod",
)


TARGET_TABLES_IN_TRUNCATE_ORDER = [
    "messages",
    "conversation",
    "candidate_stage_comment",
    "candidate_resume",
    "applications",
    "candidates",
    "import_session",
    "custom_field_definition",
    "lookup_option",
    "lookup_category",
    "user_account",
    "organization",
]


def table_exists(conn: Connection, table_name: str) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
        """
    )
    return bool(conn.execute(query, {"table_name": table_name}).scalar())


def column_exists(conn: Connection, table_name: str, column_name: str) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
        )
        """
    )
    return bool(conn.execute(query, {"table_name": table_name, "column_name": column_name}).scalar())


def fetch_rows(conn: Connection, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(text(query), params or {}).mappings().all()
    return [dict(r) for r in rows]


def executemany_insert(conn: Connection, query: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                # psycopg2 cannot adapt bare dict/list in text() parameters;
                # wrap JSON-compatible values explicitly for JSONB columns.
                normalized[key] = Json(value)
            else:
                normalized[key] = value
        normalized_rows.append(normalized)

    conn.execute(text(query), normalized_rows)


def reset_id_sequence(conn: Connection, table_name: str, id_column: str = "id") -> None:
    seq = conn.execute(
        text("SELECT pg_get_serial_sequence(:table_name, :id_column)"),
        {"table_name": table_name, "id_column": id_column},
    ).scalar()
    if not seq:
        return
    conn.execute(
        text(
            f"""
            SELECT setval(
                '{seq}',
                COALESCE((SELECT MAX({id_column}) FROM {table_name}), 1),
                (SELECT COUNT(*) > 0 FROM {table_name})
            )
            """
        )
    )


def normalize_has_transportation(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"

    normalized = str(value).strip().lower()
    truthy = {"yes", "true", "t", "1", "has transportation", "has car", "own vehicle"}
    falsy = {"no", "false", "f", "0", "no transportation"}
    remote_only = {
        "only_open_for_remote_opportunities",
        "only open for remote opportunities",
        "remote only",
        "remote opportunities",
    }

    if normalized in truthy:
        return "yes"
    if normalized in falsy:
        return "no"
    if normalized in remote_only:
        return "only_open_for_remote_opportunities"
    return None


def merge_application_custom_fields(candidate_row: dict[str, Any]) -> dict[str, Any]:
    original = candidate_row.get("custom_fields")
    if isinstance(original, dict):
        payload: dict[str, Any] = dict(original)
    elif original is None:
        payload = {}
    else:
        payload = {"__legacy_custom_fields_raw": original}

    return payload


def truncate_target(conn: Connection) -> None:
    table_csv = ", ".join(TARGET_TABLES_IN_TRUNCATE_ORDER)
    conn.execute(text(f"TRUNCATE TABLE {table_csv} RESTART IDENTITY CASCADE"))


def print_counts(label: str, counts: dict[str, int]) -> None:
    print(f"\n{label}")
    for table, count in counts.items():
        print(f"  - {table}: {count}")


def gather_source_counts(conn: Connection, source_candidate_table: str) -> dict[str, int]:
    tables = [
        "organization",
        "user_account",
        "lookup_category",
        "lookup_option",
        "custom_field_definition",
        "import_session",
        source_candidate_table,
        "candidate_resume",
        "candidate_stage_comment",
        "conversation",
        "messages",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
    return counts


def gather_target_counts(conn: Connection) -> dict[str, int]:
    tables = [
        "organization",
        "user_account",
        "lookup_category",
        "lookup_option",
        "custom_field_definition",
        "import_session",
        "candidates",
        "applications",
        "candidate_resume",
        "candidate_stage_comment",
        "conversation",
        "messages",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
    return counts


def migrate(source_conn: Connection, target_conn: Connection, truncate_before_insert: bool) -> None:
    source_candidate_table = "candidate" if table_exists(source_conn, "candidate") else "candidates"
    if not table_exists(source_conn, source_candidate_table):
        raise RuntimeError("Source DB does not contain candidate/candidates table.")

    required_target_tables = {
        "organization",
        "user_account",
        "lookup_category",
        "lookup_option",
        "custom_field_definition",
        "import_session",
        "candidates",
        "applications",
        "candidate_resume",
        "candidate_stage_comment",
        "conversation",
        "messages",
    }
    missing = [t for t in sorted(required_target_tables) if not table_exists(target_conn, t)]
    if missing:
        raise RuntimeError(f"Target DB is missing required tables: {', '.join(missing)}")

    source_has_comment_application_status = column_exists(source_conn, "candidate_stage_comment", "application_status")
    source_candidate_has_import_sheet = column_exists(source_conn, source_candidate_table, "import_sheet")
    source_candidate_has_application_status = column_exists(source_conn, source_candidate_table, "application_status")
    target_import_session_has_import_sheet = column_exists(target_conn, "import_session", "import_sheet")
    target_comment_has_application_status = column_exists(target_conn, "candidate_stage_comment", "application_status")

    source_counts = gather_source_counts(source_conn, source_candidate_table)
    print_counts("Source counts (before migration):", source_counts)

    if truncate_before_insert:
        print("\nTruncating target tables...")
        truncate_target(target_conn)

    print("\nCopying core tables...")
    organizations = fetch_rows(
        source_conn,
        """
        SELECT id, name, slug, domain, settings, created_at, updated_at
        FROM organization
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO organization (id, name, slug, domain, settings, created_at, updated_at)
        VALUES (:id, :name, :slug, :domain, :settings, :created_at, :updated_at)
        ON CONFLICT DO NOTHING
        """,
        organizations,
    )

    users = fetch_rows(
        source_conn,
        """
        SELECT id, organization_id, email, hashed_password, first_name, last_name, role, is_active, created_at, updated_at
        FROM user_account
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO user_account (
            id, organization_id, email, hashed_password, first_name, last_name, role, is_active, created_at, updated_at
        )
        VALUES (
            :id, :organization_id, :email, :hashed_password, :first_name, :last_name, :role, :is_active, :created_at, :updated_at
        )
        ON CONFLICT DO NOTHING
        """,
        users,
    )

    lookup_categories = fetch_rows(
        source_conn,
        """
        SELECT id, code, label, description, is_system, created_at
        FROM lookup_category
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO lookup_category (id, code, label, description, is_system, created_at)
        VALUES (:id, :code, :label, :description, :is_system, :created_at)
        ON CONFLICT DO NOTHING
        """,
        lookup_categories,
    )

    lookup_options = fetch_rows(
        source_conn,
        """
        SELECT id, category_id, organization_id, code, label, display_order, is_active, created_at
        FROM lookup_option
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO lookup_option (
            id, category_id, organization_id, code, label, display_order, is_active, created_at
        )
        VALUES (
            :id, :category_id, :organization_id, :code, :label, :display_order, :is_active, :created_at
        )
        ON CONFLICT DO NOTHING
        """,
        lookup_options,
    )

    custom_fields = fetch_rows(
        source_conn,
        """
        SELECT id, organization_id, field_key, label, field_type, lookup_category_id, is_required, is_active, display_order, created_at
        FROM custom_field_definition
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO custom_field_definition (
            id, organization_id, field_key, label, field_type, lookup_category_id,
            is_required, is_active, display_order, created_at
        )
        VALUES (
            :id, :organization_id, :field_key, :label, :field_type, :lookup_category_id,
            :is_required, :is_active, :display_order, :created_at
        )
        ON CONFLICT DO NOTHING
        """,
        custom_fields,
    )

    print("Copying import sessions...")
    import_session_select_cols = """
            id, organization_id, uploaded_by_user_id, original_filename,
            status, total_rows, imported_rows, skipped_rows, error_rows, summary, created_at, completed_at
    """
    if target_import_session_has_import_sheet:
        import_session_select_cols = """
            id, organization_id, uploaded_by_user_id, original_filename,
            NULL::VARCHAR AS import_sheet,
            status, total_rows, imported_rows, skipped_rows, error_rows, summary, created_at, completed_at
        """
    import_sessions = fetch_rows(
        source_conn,
        f"""
        SELECT
{import_session_select_cols}
        FROM import_session
        ORDER BY id
        """,
    )

    print("Copying candidate/application split...")
    candidate_optional_select = []
    if target_import_session_has_import_sheet and source_candidate_has_import_sheet:
        candidate_optional_select.append("import_sheet")
    if target_comment_has_application_status and source_candidate_has_application_status:
        candidate_optional_select.append("application_status")
    optional_select_sql = ""
    if candidate_optional_select:
        optional_select_sql = ",\n            " + ", ".join(candidate_optional_select)

    candidates_src = fetch_rows(
        source_conn,
        f"""
        SELECT
            id, organization_id, import_session_id,
            full_name, email, date_of_birth, created_at,
            applied_at, nationality, current_address, residency_type_id, marital_status_id,
            number_of_dependents, religion_sect, passport_validity_status_id, has_transportation,
            applied_position, applied_position_location, is_open_for_relocation, years_of_experience,
            is_employed, current_salary, expected_salary_remote, expected_salary_onsite, notice_period,
            is_overtime_flexible, is_contract_flexible, workplace_type_id, employment_type_id,
            tech_stack, education_level_id, education_completion_status_id, custom_fields{optional_select_sql},
            updated_at
        FROM {source_candidate_table}
        ORDER BY id
        """,
    )

    if target_import_session_has_import_sheet and source_candidate_has_import_sheet:
        per_session_sheet_values: dict[int, list[str]] = defaultdict(list)
        for row in candidates_src:
            session_id = row.get("import_session_id")
            import_sheet = row.get("import_sheet")
            if session_id is not None and import_sheet:
                per_session_sheet_values[session_id].append(import_sheet)

        for session in import_sessions:
            sid = session["id"]
            choices = per_session_sheet_values.get(sid, [])
            if choices:
                session["import_sheet"] = choices[0]

    import_session_insert_cols = """
            id, organization_id, uploaded_by_user_id, original_filename,
            status, total_rows, imported_rows, skipped_rows, error_rows, summary, created_at, completed_at
    """
    import_session_insert_vals = """
            :id, :organization_id, :uploaded_by_user_id, :original_filename,
            :status, :total_rows, :imported_rows, :skipped_rows, :error_rows, :summary, :created_at, :completed_at
    """
    if target_import_session_has_import_sheet:
        import_session_insert_cols = """
            id, organization_id, uploaded_by_user_id, original_filename, import_sheet,
            status, total_rows, imported_rows, skipped_rows, error_rows, summary, created_at, completed_at
        """
        import_session_insert_vals = """
            :id, :organization_id, :uploaded_by_user_id, :original_filename, :import_sheet,
            :status, :total_rows, :imported_rows, :skipped_rows, :error_rows, :summary, :created_at, :completed_at
        """
    executemany_insert(
        target_conn,
        f"""
        INSERT INTO import_session (
{import_session_insert_cols}
        )
        VALUES (
{import_session_insert_vals}
        )
        ON CONFLICT DO NOTHING
        """,
        import_sessions,
    )

    candidates_target: list[dict[str, Any]] = []
    applications_target: list[dict[str, Any]] = []
    candidate_status_by_id: dict[int, str] = {}
    candidate_org_by_id: dict[int, int] = {}
    candidate_updated_at_by_id: dict[int, Any] = {}
    for row in candidates_src:
        candidate_org_by_id[row["id"]] = row["organization_id"]
        candidate_updated_at_by_id[row["id"]] = row.get("updated_at") or row["created_at"]
        if target_comment_has_application_status and row.get("application_status") is not None:
            candidate_status_by_id[row["id"]] = row["application_status"]

        candidates_target.append(
            {
                "id": row["id"],
                "organization_id": row["organization_id"],
                "import_session_id": row["import_session_id"],
                "full_name": row["full_name"],
                "email": row["email"],
                "date_of_birth": row["date_of_birth"],
                "created_at": row["created_at"],
            }
        )

        applications_target.append(
            {
                "id": row["id"],
                "candidate_id": row["id"],
                "import_session_id": row["import_session_id"],
                "notice_period": row["notice_period"],
                "applied_at": row["applied_at"],
                "current_address": row["current_address"],
                "nationality": row["nationality"],
                "residency_type_id": row["residency_type_id"],
                "marital_status_id": row["marital_status_id"],
                "number_of_dependents": row["number_of_dependents"],
                "religion_sect": row["religion_sect"],
                "passport_validity_status_id": row["passport_validity_status_id"],
                "has_transportation": normalize_has_transportation(row.get("has_transportation")),
                "applied_position": row["applied_position"],
                "applied_position_location": row["applied_position_location"],
                "is_open_for_relocation": row["is_open_for_relocation"],
                "years_of_experience": row["years_of_experience"],
                "current_salary": row["current_salary"],
                "expected_salary_remote": row["expected_salary_remote"],
                "expected_salary_onsite": row["expected_salary_onsite"],
                "is_overtime_flexible": row["is_overtime_flexible"],
                "is_contract_flexible": row["is_contract_flexible"],
                "workplace_type_id": row["workplace_type_id"],
                "employment_type_id": row["employment_type_id"],
                "is_employed": row["is_employed"],
                "tech_stack": row["tech_stack"] if row.get("tech_stack") is not None else [],
                "education_level_id": row["education_level_id"],
                "education_completion_status_id": row["education_completion_status_id"],
                "custom_fields": merge_application_custom_fields(row),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"] or row["created_at"],
            }
        )

    executemany_insert(
        target_conn,
        """
        INSERT INTO candidates (
            id, organization_id, import_session_id, full_name, email, date_of_birth, created_at
        )
        VALUES (
            :id, :organization_id, :import_session_id, :full_name, :email, :date_of_birth, :created_at
        )
        ON CONFLICT DO NOTHING
        """,
        candidates_target,
    )

    executemany_insert(
        target_conn,
        """
        INSERT INTO applications (
            id, candidate_id, import_session_id, notice_period, applied_at, current_address, nationality,
            residency_type_id, marital_status_id, number_of_dependents, religion_sect, passport_validity_status_id,
            has_transportation, applied_position, applied_position_location, is_open_for_relocation,
            years_of_experience, current_salary, expected_salary_remote, expected_salary_onsite,
            is_overtime_flexible, is_contract_flexible, workplace_type_id, employment_type_id, is_employed,
            tech_stack, education_level_id, education_completion_status_id, custom_fields, created_at, updated_at
        )
        VALUES (
            :id, :candidate_id, :import_session_id, :notice_period, :applied_at, :current_address, :nationality,
            :residency_type_id, :marital_status_id, :number_of_dependents, :religion_sect, :passport_validity_status_id,
            :has_transportation, :applied_position, :applied_position_location, :is_open_for_relocation,
            :years_of_experience, :current_salary, :expected_salary_remote, :expected_salary_onsite,
            :is_overtime_flexible, :is_contract_flexible, :workplace_type_id, :employment_type_id, :is_employed,
            :tech_stack, :education_level_id, :education_completion_status_id, :custom_fields, :created_at, :updated_at
        )
        ON CONFLICT DO NOTHING
        """,
        applications_target,
    )

    print("Copying resume, comments, and chat tables...")
    resumes = fetch_rows(
        source_conn,
        """
        SELECT id, candidate_id, organization_id, filename, content_type, file_data, resume_info, created_at, updated_at
        FROM candidate_resume
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO candidate_resume (
            id, candidate_id, organization_id, filename, content_type, file_data, resume_info, created_at, updated_at
        )
        VALUES (
            :id, :candidate_id, :organization_id, :filename, :content_type, :file_data, :resume_info, :created_at, :updated_at
        )
        ON CONFLICT DO NOTHING
        """,
        resumes,
    )

    comments_query = """
        SELECT id, candidate_id, organization_id, stage_key, entries, updated_at
        FROM candidate_stage_comment
        ORDER BY id
    """
    if target_comment_has_application_status and source_has_comment_application_status:
        comments_query = """
            SELECT id, candidate_id, organization_id, stage_key, entries, application_status, updated_at
            FROM candidate_stage_comment
            ORDER BY id
        """
    comments = fetch_rows(source_conn, comments_query)

    existing_comment_candidate_ids: set[int] = set()
    max_comment_id = 0
    for row in comments:
        max_comment_id = max(max_comment_id, int(row["id"]))
        existing_comment_candidate_ids.add(int(row["candidate_id"]))
        if target_comment_has_application_status:
            if source_has_comment_application_status:
                if row.get("application_status") is None:
                    row["application_status"] = candidate_status_by_id.get(int(row["candidate_id"]))
            else:
                row["application_status"] = candidate_status_by_id.get(int(row["candidate_id"]))

    if target_comment_has_application_status:
        next_comment_id = max_comment_id + 1
        for candidate_id, status_value in candidate_status_by_id.items():
            if candidate_id in existing_comment_candidate_ids:
                continue
            comments.append(
                {
                    "id": next_comment_id,
                    "candidate_id": candidate_id,
                    "organization_id": candidate_org_by_id[candidate_id],
                    "stage_key": "pre_screening",
                    "entries": [],
                    "application_status": status_value,
                    "updated_at": candidate_updated_at_by_id.get(candidate_id) or datetime.now(timezone.utc),
                }
            )
            next_comment_id += 1

    comment_insert_cols = "id, candidate_id, organization_id, stage_key, entries, updated_at"
    comment_insert_vals = ":id, :candidate_id, :organization_id, :stage_key, :entries, :updated_at"
    if target_comment_has_application_status:
        comment_insert_cols = "id, candidate_id, organization_id, stage_key, entries, application_status, updated_at"
        comment_insert_vals = ":id, :candidate_id, :organization_id, :stage_key, :entries, :application_status, :updated_at"
    executemany_insert(
        target_conn,
        f"""
        INSERT INTO candidate_stage_comment (
            {comment_insert_cols}
        )
        VALUES (
            {comment_insert_vals}
        )
        ON CONFLICT DO NOTHING
        """,
        comments,
    )

    conversations = fetch_rows(
        source_conn,
        """
        SELECT id, user_account_id, title, created_at, updated_at
        FROM conversation
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO conversation (id, user_account_id, title, created_at, updated_at)
        VALUES (:id, :user_account_id, :title, :created_at, :updated_at)
        ON CONFLICT DO NOTHING
        """,
        conversations,
    )

    messages = fetch_rows(
        source_conn,
        """
        SELECT id, conversation_id, content, sender, response_data, created_at
        FROM messages
        ORDER BY id
        """,
    )
    executemany_insert(
        target_conn,
        """
        INSERT INTO messages (id, conversation_id, content, sender, response_data, created_at)
        VALUES (:id, :conversation_id, :content, :sender, :response_data, :created_at)
        ON CONFLICT DO NOTHING
        """,
        messages,
    )

    for table in TARGET_TABLES_IN_TRUNCATE_ORDER:
        reset_id_sequence(target_conn, table, "id")

    target_counts = gather_target_counts(target_conn)
    print_counts("Target counts (after migration):", target_counts)
    print("\nMigration completed successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate hr_project_database -> hr_project_database_prod")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL, help="SQLAlchemy URL for source DB")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help="SQLAlchemy URL for target DB")
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target tables before insert (default is copy-only, no delete).",
    )
    return parser.parse_args()


def mask_db_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if ":" not in rest.split("@", 1)[0]:
        return url
    credentials, host_part = rest.split("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host_part}"


def main() -> None:
    args = parse_args()
    print("Source DB:", mask_db_url(args.source_url))
    print("Target DB:", mask_db_url(args.target_url))

    source_engine = create_engine(args.source_url, future=True)
    target_engine = create_engine(args.target_url, future=True)

    source_conn = source_engine.connect()
    target_tx = target_engine.begin()

    try:
        with source_conn, target_tx as target_conn:
            migrate(
                source_conn=source_conn,
                target_conn=target_conn,
                truncate_before_insert=args.truncate_target,
            )
    except SQLAlchemyError as exc:
        print(f"\nMigration failed: {exc}")
        raise


if __name__ == "__main__":
    main()
