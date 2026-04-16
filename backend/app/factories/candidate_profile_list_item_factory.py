"""Build CandidateProfileListItem rows for the candidates table API."""

from typing import Any, Optional

from ..dtos.hr_stage_comments import HrStageCommentsRead
from ..schemas.candidate import CandidateProfileListItem
from .candidate_fields import optional_application_status


def build_candidate_profile_list_items(
    *,
    rows: list[Any],
    apps_map: dict[int, Any],
    status_map: dict[int, Optional[str]],
    hr_map: dict[int, HrStageCommentsRead],
) -> list[CandidateProfileListItem]:
    items: list[CandidateProfileListItem] = []
    for row in rows:
        app = apps_map.get(row.id)
        items.append(
            CandidateProfileListItem(
                id=row.id,
                organization_id=row.organization_id,
                import_session_id=row.import_session_id,
                full_name=row.full_name,
                email=row.email,
                date_of_birth=row.date_of_birth,
                created_at=row.created_at,
                applied_position=app.applied_position if app else None,
                is_open_for_relocation=app.is_open_for_relocation if app else None,
                application_status=optional_application_status(status_map.get(row.id)),
                hr_stage_comments=hr_map.get(row.id) or HrStageCommentsRead(),
            )
        )
    return items
