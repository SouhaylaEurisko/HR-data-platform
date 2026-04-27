"""
Typed Pydantic AI wrapper for chatbot agents.

Builds ``pydantic_ai.Agent`` instances that return validated Pydantic models
directly, so every agent in this service works with typed outputs instead of
raw JSON dicts.

The module exposes three primitives used by every migrated agent:

* ``build_agent(output_type, system_prompt, *, temperature)`` — factory that
  returns an ``Agent`` bound to the OpenAI model configured in
  ``app/config/config.py``.  The agent is created with a history processor
  that re-adds the system prompt at the head of every request when the
  caller-supplied ``message_history`` does not carry one — the chatbot stores
  only ``user``/``assistant`` turns in the DB, so this is required to keep
  multi-turn system-prompt semantics.
* ``to_message_history(history)`` — converts the project's multi-turn history
  format (``list[dict[str, str]]`` with role/content keys) into the
  ``pydantic_ai`` message types (``ModelRequest`` / ``ModelResponse``).
* ``run_typed(agent, user_message, *, context, conversation_history)`` — awaits
  the agent run and returns the validated output instance.  Translates
  ``UnexpectedModelBehavior`` and ``ValidationError`` into ``RuntimeError`` so
  the existing ``try/except RuntimeError`` blocks in the agent code keep
  catching LLM parse failures unchanged.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIChatModel

from ..config import config

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT", bound=BaseModel)

_DEFAULT_MODEL = "gpt-4o-mini"


def _resolve_model_name(override: Optional[str] = None) -> str:
    """Return the OpenAI model name, preferring explicit override then env/config."""
    return override or config.openai_model or _DEFAULT_MODEL


def _make_system_prompt_reinjector(
    system_prompt: str,
) -> Callable[[List[ModelMessage]], List[ModelMessage]]:
    """
    Build a history processor that guarantees ``system_prompt`` leads the request.

    Pydantic AI suppresses the agent's configured ``system_prompt`` whenever a
    non-empty ``message_history`` is supplied to ``Agent.run``. The chatbot's
    persisted history only contains ``user``/``assistant`` turns, so without
    this processor every follow-up run would lose its instructions. The
    processor is a no-op once any ``SystemPromptPart`` is already present
    (e.g. the empty-history case where Pydantic AI injected it for us).
    """

    def reinject(messages: List[ModelMessage]) -> List[ModelMessage]:
        if not messages:
            return messages
        for msg in messages:
            for part in getattr(msg, "parts", []) or []:
                if isinstance(part, SystemPromptPart):
                    return messages

        first = messages[0]
        new_system_part = SystemPromptPart(content=system_prompt)
        if isinstance(first, ModelRequest):
            new_first = ModelRequest(parts=[new_system_part, *list(first.parts)])
            return [new_first, *list(messages[1:])]

        return [ModelRequest(parts=[new_system_part]), *list(messages)]

    return reinject


def build_agent(
    output_type: Type[OutputT],
    system_prompt: str,
    *,
    temperature: float = 0.2,
    model_name: Optional[str] = None,
) -> Agent[Any, OutputT]:
    """
    Build a Pydantic AI agent that returns a validated ``output_type`` instance.

    Args:
        output_type:   Pydantic model class the agent must produce.
        system_prompt: Instructions used as the system message for every run.
        temperature:   Sampling temperature (low = deterministic).
        model_name:    Optional override; defaults to ``config.openai_model``.
    """
    model = OpenAIChatModel(_resolve_model_name(model_name))
    return Agent(
        model=model,
        output_type=output_type,
        system_prompt=system_prompt,
        model_settings={"temperature": temperature},
        history_processors=[_make_system_prompt_reinjector(system_prompt)],
    )


def to_message_history(
    conversation_history: Optional[List[Dict[str, str]]],
) -> List[ModelMessage]:
    """
    Convert ``[{"role": "user" | "assistant", "content": str}]`` to Pydantic AI
    messages. Empty/missing content is skipped. Unknown roles are ignored.
    """
    if not conversation_history:
        return []

    messages: List[ModelMessage] = []
    for entry in conversation_history:
        if not isinstance(entry, dict):
            continue
        role = (entry.get("role") or "").strip().lower()
        content = entry.get("content")
        if not content:
            continue
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role in ("assistant", "system"):
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


async def run_typed(
    agent: Agent[Any, OutputT],
    user_message: str,
    *,
    context: str = "LLM call",
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> OutputT:
    """
    Run ``agent`` and return its validated output.

    Args:
        agent:                Typed agent built via ``build_agent``.
        user_message:         The user-facing prompt for this run.
        context:              Label used when re-raising as ``RuntimeError``.
        conversation_history: Optional prior turns in the project's
                              ``[{"role": ..., "content": ...}]`` format.

    Pydantic AI failures that indicate the model could not produce a valid
    structured output (``UnexpectedModelBehavior``, ``ValidationError``) are
    re-raised as ``RuntimeError(f"{context}: ...")`` so existing
    ``except RuntimeError`` branches in the agent code (cv_info, hr_feedback,
    candidate_comparison) remain effective. Network and provider-level errors
    are left to propagate as before.
    """
    history = to_message_history(conversation_history)
    try:
        result = await agent.run(user_message, message_history=history)
    except UnexpectedModelBehavior as exc:
        raise RuntimeError(f"{context}: model returned unexpected output — {exc}") from exc
    except ValidationError as exc:
        raise RuntimeError(f"{context}: output failed validation — {exc}") from exc

    return result.output


def attach_sql_output_validator(
    agent: Agent[Any, OutputT],
    *,
    fields: Sequence[str] = ("sql",),
) -> Agent[Any, OutputT]:
    """
    Register an ``output_validator`` on ``agent`` that asks the model to retry
    whenever a SQL field on the validated output is obviously malformed.

    For each name in ``fields``, the validator checks that the value is:

    * a non-empty string after stripping whitespace,
    * a single statement (no ``;``-separated multi-statement payloads), and
    * starts with ``SELECT`` or ``WITH`` (CTE form ``WITH ... SELECT``).

    Any failure raises :class:`pydantic_ai.exceptions.ModelRetry` with a
    feedback string describing the issue, which Pydantic AI uses to re-prompt
    the model. After ``Agent.retries`` attempts (default 1), Pydantic AI
    surfaces ``UnexpectedModelBehavior`` — already translated to
    ``RuntimeError`` by :func:`run_typed`, so existing
    ``except RuntimeError`` branches in agent code remain effective.

    Stronger SQL safety (forbidden keywords, identifier allow-lists, etc.) is
    intentionally left to ``app/utils/db_utils.execute_safe_query``; this
    validator only catches the cheap, obvious mistakes the LLM occasionally
    makes so we don't waste a DB round-trip on a query that can't possibly
    work. Returns the same agent, so calls can be chained:

        agent = attach_sql_output_validator(build_agent(...))
    """

    @agent.output_validator
    def _validate_sql(data: OutputT) -> OutputT:
        for field_name in fields:
            value = getattr(data, field_name, None)
            if not isinstance(value, str) or not value.strip():
                raise ModelRetry(
                    f"Field '{field_name}' must be a non-empty SELECT statement; "
                    f"received empty or non-string value."
                )

            stripped = value.strip().rstrip(";").strip()
            upper = stripped.upper()
            if not (upper.startswith("SELECT") or upper.startswith("WITH ")):
                preview = stripped[:80].replace("\n", " ")
                raise ModelRetry(
                    f"Field '{field_name}' must start with SELECT (or WITH ... SELECT). "
                    f"Got: {preview!r}. Rewrite as a single SELECT query."
                )

            stmts = [s for s in stripped.split(";") if s.strip()]
            if len(stmts) > 1:
                raise ModelRetry(
                    f"Field '{field_name}' must contain exactly one statement; "
                    f"found {len(stmts)} `;`-separated statements. "
                    f"Combine into a single SELECT or remove the extras."
                )
        return data

    return agent
