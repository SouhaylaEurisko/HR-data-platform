"""
Chat service — orchestrates chatbot HTTP calls and candidate list queries.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from ..config import config
from ..models.chat import ChatResponse, ChatSearchFilters, AggregationResult
from ..models.candidates import CandidateRead
from ..services.candidate_service import list_candidates
from ..clients.chatbot_client import ChatbotClient


logger = logging.getLogger(__name__)

CHATBOT_TIMEOUT_S = 30.0
AGGREGATION_PAGE_SIZE = 1000
CHAT_TOP_N = 10

def _error_response(reply: str) -> ChatResponse:
    return ChatResponse(
        reply=reply,
        filters=ChatSearchFilters(),
        total_matches=0,
        top_candidates=[],
        aggregations=None,
    )


_SERVICE_DOWN_REPLY = (
    "Sorry, I encountered an error connecting to the AI service. Please try again."
)


def _list_candidates_for_chat(
    db: Session,
    filters: ChatSearchFilters,
    page_size: int,
) -> tuple[List[CandidateRead], int]:
    """Run list_candidates with full chat filters"""
    result = list_candidates(
        db=db,
        page=1,
        page_size=page_size,
        search=filters.name,
        applied_position=filters.position,
        email=filters.email,
        nationality=filters.nationality,
        min_years_experience=filters.min_years_experience,
        max_years_experience=filters.max_years_experience,
        min_expected_salary_remote=filters.min_expected_salary_remote,
        max_expected_salary_remote=filters.max_expected_salary_remote,
        min_expected_salary_onsite=filters.min_expected_salary_onsite,
        max_expected_salary_onsite=filters.max_expected_salary_onsite,
    )
    return result.items, result.total


def _opt_str(data: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        v = data.get(k)
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
    return None


def _opt_float(data: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = data.get(k)
        if v is None:
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError):
            continue
    return None


def _build_filters_from_extract(data: Dict[str, Any]) -> ChatSearchFilters:
    """Map chatbot JSON to filters; supports multiple key aliases per field."""
    return ChatSearchFilters(
        name=_opt_str(data, "name", "full_name", "candidate_name", "search"),
        position=_opt_str(data, "position", "applied_position", "job_title", "role"),
        email=_opt_str(data, "email", "email_address"),
        nationality=_opt_str(data, "nationality", "country"),
        min_years_experience=_opt_float(
            data, "min_years_experience", "min_experience", "min_years"
        ),
        max_years_experience=_opt_float(
            data, "max_years_experience", "max_experience", "max_years"
        ),
        min_expected_salary_remote=_opt_float(
            data,
            "min_expected_salary_remote",
            "min_remote_salary",
            "min_salary_remote",
        ),
        max_expected_salary_remote=_opt_float(
            data,
            "max_expected_salary_remote",
            "max_remote_salary",
            "max_salary_remote",
        ),
        min_expected_salary_onsite=_opt_float(
            data,
            "min_expected_salary_onsite",
            "min_onsite_salary",
            "min_salary_onsite",
        ),
        max_expected_salary_onsite=_opt_float(
            data,
            "max_expected_salary_onsite",
            "max_onsite_salary",
            "max_salary_onsite",
        ),
    )


def _compute_aggregation(candidates: List[CandidateRead]) -> Optional[AggregationResult]:
    if not candidates:
        return None
    salaries = [float(c.current_salary) for c in candidates if c.current_salary is not None]
    experiences = [
        float(c.years_of_experience)
        for c in candidates
        if c.years_of_experience is not None
    ]
    return AggregationResult(
        total_count=len(candidates),
        avg_salary=sum(salaries) / len(salaries) if salaries else None,
        avg_experience=sum(experiences) / len(experiences) if experiences else None,
        min_salary=min(salaries) if salaries else None,
        max_salary=max(salaries) if salaries else None,
        min_experience=min(experiences) if experiences else None,
        max_experience=max(experiences) if experiences else None,
    )


def _generate_reply(
    classify_data: Dict[str, Any],
    total_matches: int,
    aggregation: Optional[AggregationResult],
) -> str:
    question_type = classify_data.get("question_type") or "conversational"

    if question_type == "greeting":
        return (
            "Hello! I can help you search for candidates. Try asking me something like "
            "'Show me backend engineers' or 'What's the average salary?'"
        )

    if question_type == "aggregation":
        if aggregation:
            parts = []
            if aggregation.total_count:
                parts.append(f"Found {aggregation.total_count} candidates")
            if aggregation.avg_salary is not None:
                parts.append(f"Average salary: ${aggregation.avg_salary:,.0f}")
            if aggregation.avg_experience is not None:
                parts.append(f"Average experience: {aggregation.avg_experience:.1f} years")
            return ". ".join(parts) + "." if parts else f"I found {total_matches} candidates matching your query."
        return f"I found {total_matches} candidates matching your query."

    if question_type == "candidate_search":
        if total_matches > 0:
            return (
                f"I found {total_matches} candidate(s) matching your search. "
                "Here are the top results."
            )
        return "I couldn't find any candidates matching your search. Try adjusting your filters."

    return f"I found {total_matches} candidate(s). How can I help you further?"


async def handle_chat_message(message: str, db: Session) -> ChatResponse:
    """
    Classify the message via chatbot service, optionally extract filters,
    compute aggregations, and return top candidate rows.
    """
    chatbot_url = config.chatbot_service_url

    try:
        async with httpx.AsyncClient(timeout=CHATBOT_TIMEOUT_S) as http_client:
            bot = ChatbotClient(chatbot_url, http_client)

            classify_data = await bot.classify(message)

            filters = ChatSearchFilters()
            if classify_data.get("is_candidate_related"):
                extract_data = await bot.extract_filters(message)
                filters = _build_filters_from_extract(extract_data)

            aggregation: Optional[AggregationResult] = None
            items: List[CandidateRead] = []
            total_matches = 0

            needs_agg = (
                classify_data.get("requires_data")
                and (await bot.detect_aggregation(message)).get("is_aggregation")
            )

            if needs_agg:
                items, total_matches = _list_candidates_for_chat(
                    db, filters, AGGREGATION_PAGE_SIZE
                )
                aggregation = _compute_aggregation(items)
            else:
                items, total_matches = _list_candidates_for_chat(
                    db, filters, CHAT_TOP_N
                )

            top = items[:CHAT_TOP_N]
            reply = _generate_reply(classify_data, total_matches, aggregation)

            return ChatResponse(
                reply=reply,
                filters=filters,
                total_matches=total_matches,
                top_candidates=top,
                aggregations=aggregation,
            )

    except httpx.RequestError:
        logger.warning("Chatbot service unreachable at %s", chatbot_url)
        return ChatResponse(
            reply=_SERVICE_DOWN_REPLY,
            filters=ChatSearchFilters(),
            total_matches=0,
            top_candidates=[],
            aggregations=None,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Chatbot HTTP error: %s %s",
            exc.response.status_code,
            exc.response.text[:200] if exc.response else "",
        )
        return _error_response("Sorry, something went wrong. Please try again.")
    except (ValueError, KeyError, TypeError) as exc:
        logger.exception("Chat pipeline data error: %s", exc)
        return _error_response("Sorry, something went wrong. Please try again.")
    except Exception:
        logger.exception("Unexpected error in handle_chat_message")
        return _error_response("Sorry, something went wrong. Please try again.")
