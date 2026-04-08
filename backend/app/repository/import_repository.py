"""Import session queries and import row persistence."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.applications import Application
from ..models.candidates import CandidateProfile
from ..models.import_session import ImportSession


def import_filename_exists(db: Session, org_id: int, filename_normalized_lower: str) -> bool:
    """True if any session in the org used this filename (case-insensitive)."""
    if not filename_normalized_lower:
        return False
    return (
        db.query(ImportSession.id)
        .filter(
            ImportSession.organization_id == org_id,
            func.lower(ImportSession.original_filename) == filename_normalized_lower,
        )
        .first()
        is not None
    )


def distinct_import_sheet_strings_for_filename(
    db: Session, org_id: int, filename_normalized_lower: str
) -> list[str]:
    """Distinct import_sheet values for sessions matching filename (case-insensitive)."""
    if not filename_normalized_lower:
        return []
    rows = (
        db.query(ImportSession.import_sheet)
        .filter(
            ImportSession.organization_id == org_id,
            func.lower(ImportSession.original_filename) == filename_normalized_lower,
            ImportSession.import_sheet.isnot(None),
        )
        .distinct()
        .all()
    )
    return [str(sv) for (sv,) in rows if sv is not None]


def create_pending_import_session(
    db: Session,
    *,
    org_id: int,
    user_id: int,
    original_filename: str,
) -> ImportSession:
    session = ImportSession(
        organization_id=org_id,
        uploaded_by_user_id=user_id,
        original_filename=original_filename,
        status="pending",
    )
    db.add(session)
    db.flush()
    return session


def get_import_session_by_id(db: Session, session_id: int) -> Optional[ImportSession]:
    return db.query(ImportSession).filter_by(id=session_id).first()


def mark_import_session_processing(db: Session, session: ImportSession) -> None:
    session.status = "processing"
    db.flush()


def insert_imported_candidate_row(
    db: Session, profile_kw: Dict[str, Any], app_kw: Dict[str, Any]
) -> None:
    """Insert CandidateProfile, flush for id, then Application for one import row."""
    profile = CandidateProfile(**profile_kw)
    db.add(profile)
    db.flush()
    app_kw["candidate_id"] = profile.id
    db.add(Application(**app_kw))


def apply_import_session_completion(
    session: ImportSession,
    *,
    import_sheet: Optional[str],
    total_rows: int,
    imported_rows: int,
    skipped_rows: int,
    error_rows: int,
    completed_at: datetime,
    summary: Dict[str, Any],
) -> None:
    session.import_sheet = import_sheet
    session.total_rows = total_rows
    session.imported_rows = imported_rows
    session.skipped_rows = skipped_rows
    session.error_rows = error_rows
    session.status = "completed"
    session.completed_at = completed_at
    session.summary = summary
