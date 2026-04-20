"""
Candidate service — listing and detail with org-scoped filters and eager loading.

HTTP list endpoint exposes name + position only; optional kwargs support chat-rich filters.
DB queries live in repository.candidates_repository.
"""

from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol

from ..constants import CandidateList
from ..data.candidate_update_fields import APPLICATION_UPDATE_KEYS, PROFILE_UPDATE_KEYS
from ..dtos.candidate import CandidateListFilterParams
from ..dtos.hr_stage_comments import HrStageCommentsRead
from ..factories.candidate_fields import (
    related_summaries_from_group_rows,
    resolved_nationality_from_application,
    transport_enum_from_value,
)
from ..factories.candidate_profile_list_item_factory import build_candidate_profile_list_items
from ..factories.candidate_read_factory import build_candidate_read
from ..schemas.candidate import (
    CandidateApplicationStatusResponse,
    CandidateApplicationStatusUpdate,
    CandidateHrStageCommentCreate,
    CandidateHrStageCommentsUpdateResponse,
    CandidateListResponse,
    CandidateProfileListResponse,
    CandidateProfilePatchResponse,
    CandidateRead,
    CandidateUpdate,
)
from ..repository.candidates_repository import (
    CandidatesRepositoryProtocol,
)
from ..repository.candidate_stage_comments_repository import (
    CandidateStageCommentsRepositoryProtocol,
)
from ..dtos.hr_stage_comments import (
    hr_stage_comments_latest_only,
    json_rows_to_hr_stage_comments_read,
)

# Sortable columns exposed on the candidates table (and created_at default)
SortBy = Literal[
    "created_at",
    "full_name",
]


@dataclass(frozen=True, slots=True)
class _ListFilters:
    """Internal: HTTP passes name+position; chat may pass additional bounds."""

    search: Optional[str] = None
    applied_position: Optional[str] = None
    email: Optional[str] = None
    nationality: Optional[str] = None
    min_years_experience: Optional[float] = None
    max_years_experience: Optional[float] = None
    min_expected_salary_remote: Optional[float] = None
    max_expected_salary_remote: Optional[float] = None
    min_expected_salary_onsite: Optional[float] = None
    max_expected_salary_onsite: Optional[float] = None


def _filters_to_repo_params(f: _ListFilters) -> CandidateListFilterParams:
    return CandidateListFilterParams(
        search=f.search,
        applied_position=f.applied_position,
        email=f.email,
        nationality=f.nationality,
        min_years_experience=f.min_years_experience,
        max_years_experience=f.max_years_experience,
        min_expected_salary_remote=f.min_expected_salary_remote,
        max_expected_salary_remote=f.max_expected_salary_remote,
        min_expected_salary_onsite=f.min_expected_salary_onsite,
        max_expected_salary_onsite=f.max_expected_salary_onsite,
    )


class CandidateServiceProtocol(Protocol):
    def list_candidates(
        self,
        *,
        org_id: int = 1,
        page: int = CandidateList.DEFAULT_PAGE,
        page_size: int = CandidateList.DEFAULT_PAGE_SIZE,
        search: Optional[str] = None,
        applied_position: Optional[str] = None,
        email: Optional[str] = None,
        nationality: Optional[str] = None,
        min_years_experience: Optional[float] = None,
        max_years_experience: Optional[float] = None,
        min_expected_salary_remote: Optional[float] = None,
        max_expected_salary_remote: Optional[float] = None,
        min_expected_salary_onsite: Optional[float] = None,
        max_expected_salary_onsite: Optional[float] = None,
        sort_by: SortBy = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> CandidateListResponse: ...
    def list_candidate_profiles(
        self,
        *,
        org_id: int = 1,
        page: int = CandidateList.DEFAULT_PAGE,
        page_size: int = CandidateList.DEFAULT_PAGE_SIZE,
        search: Optional[str] = None,
        applied_position: Optional[str] = None,
        sort_by: Literal[
            "created_at", "full_name", "email", "date_of_birth", "applied_position"
        ] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> CandidateProfileListResponse: ...
    def append_candidate_hr_stage_comment(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateHrStageCommentCreate,
    ) -> Optional[CandidateHrStageCommentsUpdateResponse]: ...
    def update_candidate_application_status(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateApplicationStatusUpdate,
    ) -> Optional[CandidateApplicationStatusResponse]: ...
    def update_candidate_profile(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateUpdate,
    ) -> Optional[CandidateProfilePatchResponse]: ...
    def delete_candidate_profile(self, candidate_id: int, org_id: int) -> bool: ...
    def get_candidate_by_id(self, candidate_id: int, org_id: int = 1) -> Optional[CandidateRead]: ...


class CandidateService:
    def __init__(
        self,
        candidates_repo: CandidatesRepositoryProtocol,
        stage_comments_repo: CandidateStageCommentsRepositoryProtocol,
    ) -> None:
        self._candidates_repo = candidates_repo
        self._stage_comments_repo = stage_comments_repo

    def _fetch_hr_stage_comments_for_candidate(
        self,
        *,
        org_id: int,
        candidate_id: int,
    ) -> HrStageCommentsRead:
        rows = self._stage_comments_repo.list_comments_for_candidate(
            org_id=org_id,
            candidate_id=candidate_id,
        )
        return json_rows_to_hr_stage_comments_read(rows)

    def _fetch_hr_stage_comments_for_candidate_ids(
        self,
        *,
        org_id: int,
        candidate_ids: list[int],
        latest_only: bool = False,
    ) -> dict[int, HrStageCommentsRead]:
        if not candidate_ids:
            return {}
        rows = self._stage_comments_repo.list_comments_for_candidates(
            org_id=org_id,
            candidate_ids=candidate_ids,
        )
        by_cand: dict[int, list] = {}
        for row in rows:
            by_cand.setdefault(row.candidate_id, []).append(row)

        out: dict[int, HrStageCommentsRead] = {}
        for cid in candidate_ids:
            full = json_rows_to_hr_stage_comments_read(by_cand.get(cid, []))
            out[cid] = hr_stage_comments_latest_only(full) if latest_only else full
        return out

    def _build_candidate_profile_patch_response(
        self,
        *,
        candidate_id: int,
        org_id: int,
        response_keys: set[str],
    ) -> Optional[CandidateProfilePatchResponse]:
        candidate = self._candidates_repo.get_candidate_profile_by_id_org(candidate_id, org_id)
        if candidate is None:
            return None

        application = self._candidates_repo.get_latest_application_for_candidate(candidate_id)
        updated_at = application.updated_at if application is not None else candidate.created_at
        payload: dict[str, Any] = {"updated_at": updated_at}

        for key in response_keys:
            if key in PROFILE_UPDATE_KEYS:
                payload[key] = getattr(candidate, key)
            elif key == "nationality":
                payload["nationality"] = resolved_nationality_from_application(application)
            elif key in APPLICATION_UPDATE_KEYS:
                if application is None:
                    payload[key] = [] if key == "tech_stack" else None
                elif key == "has_transportation":
                    payload[key] = transport_enum_from_value(application.has_transportation)
                elif key == "tech_stack":
                    payload[key] = list(application.tech_stack or [])
                else:
                    payload[key] = getattr(application, key)

        return CandidateProfilePatchResponse(**payload)

    def list_candidates(
        self,
        *,
        org_id: int = 1,
        page: int = CandidateList.DEFAULT_PAGE,
        page_size: int = CandidateList.DEFAULT_PAGE_SIZE,
        search: Optional[str] = None,
        applied_position: Optional[str] = None,
        email: Optional[str] = None,
        nationality: Optional[str] = None,
        min_years_experience: Optional[float] = None,
        max_years_experience: Optional[float] = None,
        min_expected_salary_remote: Optional[float] = None,
        max_expected_salary_remote: Optional[float] = None,
        min_expected_salary_onsite: Optional[float] = None,
        max_expected_salary_onsite: Optional[float] = None,
        sort_by: SortBy = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> CandidateListResponse:
        def _s(v: Optional[str]) -> Optional[str]:
            if not v or not str(v).strip():
                return None
            return str(v).strip()

        flt = _ListFilters(
            search=_s(search),
            applied_position=_s(applied_position),
            email=_s(email),
            nationality=_s(nationality),
            min_years_experience=min_years_experience,
            max_years_experience=max_years_experience,
            min_expected_salary_remote=min_expected_salary_remote,
            max_expected_salary_remote=max_expected_salary_remote,
            min_expected_salary_onsite=min_expected_salary_onsite,
            max_expected_salary_onsite=max_expected_salary_onsite,
        )
        total, rows = self._candidates_repo.fetch_filtered_candidates_page(
            org_id=org_id,
            filters=_filters_to_repo_params(flt),
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        items = [
            x for x in (self.get_candidate_by_id(c.id, org_id=org_id) for c in rows) if x is not None
        ]
        return CandidateListResponse(items=items, total=total, page=page, page_size=page_size)

    def list_candidate_profiles(
        self,
        *,
        org_id: int = 1,
        page: int = CandidateList.DEFAULT_PAGE,
        page_size: int = CandidateList.DEFAULT_PAGE_SIZE,
        search: Optional[str] = None,
        applied_position: Optional[str] = None,
        sort_by: Literal[
            "created_at", "full_name", "email", "date_of_birth", "applied_position"
        ] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> CandidateProfileListResponse:
        total, rows = self._candidates_repo.fetch_profile_list_page(
            org_id=org_id,
            search=search,
            applied_position=applied_position,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        ids = [r.id for r in rows]
        apps_map = self._candidates_repo.latest_applications_by_candidate_ids(ids)
        status_map = self._candidates_repo.latest_application_status_by_candidate_ids(org_id, ids)
        hr_map = self._fetch_hr_stage_comments_for_candidate_ids(
            org_id=org_id,
            candidate_ids=ids,
            latest_only=False,
        )

        items = build_candidate_profile_list_items(
            rows=rows,
            apps_map=apps_map,
            status_map=status_map,
            hr_map=hr_map,
        )
        return CandidateProfileListResponse(items=items, total=total, page=page, page_size=page_size)

    def append_candidate_hr_stage_comment(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateHrStageCommentCreate,
    ) -> Optional[CandidateHrStageCommentsUpdateResponse]:
        if not self._candidates_repo.append_hr_stage_comment_entry(
            candidate_id=candidate_id,
            org_id=org_id,
            stage_key=body.stage,
            text=body.text,
        ):
            return None
        return CandidateHrStageCommentsUpdateResponse(
            hr_stage_comments=self._fetch_hr_stage_comments_for_candidate(
                org_id=org_id,
                candidate_id=candidate_id,
            )
        )

    def update_candidate_application_status(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateApplicationStatusUpdate,
    ) -> Optional[CandidateApplicationStatusResponse]:
        if not self._candidates_repo.set_application_status_on_candidate_stage_comments(
            candidate_id=candidate_id,
            org_id=org_id,
            status_value=body.application_status.value,
        ):
            return None
        return CandidateApplicationStatusResponse(
            candidate_id=candidate_id,
            application_status=body.application_status,
        )

    def update_candidate_profile(
        self,
        candidate_id: int,
        org_id: int,
        body: CandidateUpdate,
    ) -> Optional[CandidateProfilePatchResponse]:
        if self._candidates_repo.get_candidate_profile_by_id_org(candidate_id, org_id) is None:
            return None

        data = body.model_dump(exclude_unset=True)
        response_keys = set(data.keys())

        if not data:
            return self._build_candidate_profile_patch_response(
                candidate_id=candidate_id,
                org_id=org_id,
                response_keys=set(),
            )

        profile_updates = {k: data.pop(k) for k in list(data.keys()) if k in PROFILE_UPDATE_KEYS}

        application_updates: dict[str, Any] = {}
        for key in list(data.keys()):
            if key == "has_transportation":
                application_updates[key] = transport_enum_from_value(data.pop(key))
            elif key in APPLICATION_UPDATE_KEYS:
                if key == "nationality":
                    v = data.pop(key)
                    application_updates[key] = (
                        str(v).strip()[:100] if v is not None and str(v).strip() else None
                    )
                else:
                    application_updates[key] = data.pop(key)

        if not profile_updates and not application_updates:
            return self._build_candidate_profile_patch_response(
                candidate_id=candidate_id,
                org_id=org_id,
                response_keys=set(),
            )

        if not self._candidates_repo.persist_candidate_profile_patch(
            candidate_id=candidate_id,
            org_id=org_id,
            profile_updates=profile_updates,
            application_updates=application_updates,
        ):
            return None

        return self._build_candidate_profile_patch_response(
            candidate_id=candidate_id,
            org_id=org_id,
            response_keys=response_keys,
        )

    def delete_candidate_profile(self, candidate_id: int, org_id: int) -> bool:
        return self._candidates_repo.delete_candidate_profile_for_org(candidate_id, org_id)

    def get_candidate_by_id(self, candidate_id: int, org_id: int = 1) -> Optional[CandidateRead]:
        candidate = self._candidates_repo.get_candidate_profile_by_id_org(candidate_id, org_id)
        if candidate is None:
            return None
        application = self._candidates_repo.get_latest_application_for_candidate(candidate.id)
        import_filename = candidate.import_session.original_filename if candidate.import_session else None
        import_sheet = None
        if candidate.import_session and candidate.import_session.import_sheet:
            s = str(candidate.import_session.import_sheet).strip()
            import_sheet = s or None
        app_idx, app_total, row_list = self._candidates_repo.get_shared_email_application_context(
            org_id=org_id,
            candidate_id=candidate_id,
            email=candidate.email,
        )
        related = related_summaries_from_group_rows(row_list)
        hr_comments = self._fetch_hr_stage_comments_for_candidate(
            org_id=org_id,
            candidate_id=candidate_id,
        )
        application_status_raw = self._candidates_repo.fetch_latest_application_status(
            candidate_id, org_id
        )

        return build_candidate_read(
            candidate=candidate,
            application=application,
            import_filename=import_filename,
            import_sheet=import_sheet,
            related=related,
            hr_comments=hr_comments,
            application_status_raw=application_status_raw,
            application_index=app_idx,
            application_total=app_total,
        )
