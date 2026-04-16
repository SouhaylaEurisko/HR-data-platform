"""Import session queries and import row persistence."""

from datetime import datetime
from typing import Any, Dict, Optional, Protocol

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..factories.import_session_factory import build_pending_import_session
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
    session = build_pending_import_session(
        org_id=org_id,
        user_id=user_id,
        original_filename=original_filename,
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


def commit_import_transaction(db: Session) -> None:
    """Commit after import Phase A (analyze) or other multi-step import DB work."""
    db.commit()


def complete_import_session_and_commit(
    db: Session,
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
    """Apply import session completion fields and commit (Phase B tail)."""
    apply_import_session_completion(
        session,
        import_sheet=import_sheet,
        total_rows=total_rows,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
        error_rows=error_rows,
        completed_at=completed_at,
        summary=summary,
    )
    db.commit()


class ImportRepositoryProtocol(Protocol):
    def import_filename_exists(self, org_id: int, filename_normalized_lower: str) -> bool: ...
    def distinct_import_sheet_strings_for_filename(
        self,
        org_id: int,
        filename_normalized_lower: str,
    ) -> list[str]: ...
    def create_pending_import_session(
        self,
        *,
        org_id: int,
        user_id: int,
        original_filename: str,
    ) -> ImportSession: ...
    def get_import_session_by_id(self, session_id: int) -> Optional[ImportSession]: ...
    def mark_import_session_processing(self, session: ImportSession) -> None: ...
    def insert_imported_candidate_row(self, profile_kw: Dict[str, Any], app_kw: Dict[str, Any]) -> None: ...
    def apply_import_session_completion(
        self,
        session: ImportSession,
        *,
        import_sheet: Optional[str],
        total_rows: int,
        imported_rows: int,
        skipped_rows: int,
        error_rows: int,
        completed_at: datetime,
        summary: Dict[str, Any],
    ) -> None: ...
    def commit_import_transaction(self) -> None: ...
    def complete_import_session_and_commit(
        self,
        session: ImportSession,
        *,
        import_sheet: Optional[str],
        total_rows: int,
        imported_rows: int,
        skipped_rows: int,
        error_rows: int,
        completed_at: datetime,
        summary: Dict[str, Any],
    ) -> None: ...


class ImportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def import_filename_exists(self, org_id: int, filename_normalized_lower: str) -> bool:
        return import_filename_exists(self._db, org_id, filename_normalized_lower)

    def distinct_import_sheet_strings_for_filename(
        self,
        org_id: int,
        filename_normalized_lower: str,
    ) -> list[str]:
        return distinct_import_sheet_strings_for_filename(
            self._db,
            org_id,
            filename_normalized_lower,
        )

    def create_pending_import_session(
        self,
        *,
        org_id: int,
        user_id: int,
        original_filename: str,
    ) -> ImportSession:
        return create_pending_import_session(
            self._db,
            org_id=org_id,
            user_id=user_id,
            original_filename=original_filename,
        )

    def get_import_session_by_id(self, session_id: int) -> Optional[ImportSession]:
        return get_import_session_by_id(self._db, session_id)

    def mark_import_session_processing(self, session: ImportSession) -> None:
        mark_import_session_processing(self._db, session)

    def insert_imported_candidate_row(self, profile_kw: Dict[str, Any], app_kw: Dict[str, Any]) -> None:
        insert_imported_candidate_row(self._db, profile_kw, app_kw)

    def apply_import_session_completion(
        self,
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
        apply_import_session_completion(
            session,
            import_sheet=import_sheet,
            total_rows=total_rows,
            imported_rows=imported_rows,
            skipped_rows=skipped_rows,
            error_rows=error_rows,
            completed_at=completed_at,
            summary=summary,
        )

    def commit_import_transaction(self) -> None:
        commit_import_transaction(self._db)

    def complete_import_session_and_commit(
        self,
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
        complete_import_session_and_commit(
            self._db,
            session,
            import_sheet=import_sheet,
            total_rows=total_rows,
            imported_rows=imported_rows,
            skipped_rows=skipped_rows,
            error_rows=error_rows,
            completed_at=completed_at,
            summary=summary,
        )
