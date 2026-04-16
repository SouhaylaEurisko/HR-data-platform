"""Build ImportSession ORM instances (persistence remains in import_repository)."""

from ..models.import_session import ImportSession


def build_pending_import_session(
    *,
    org_id: int,
    user_id: int,
    original_filename: str,
) -> ImportSession:
    return ImportSession(
        organization_id=org_id,
        uploaded_by_user_id=user_id,
        original_filename=original_filename,
        status="pending",
    )
