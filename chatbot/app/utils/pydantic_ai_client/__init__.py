"""Typed Pydantic AI client wrapper used by chatbot agents."""

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

from ...config import config
from ...config.agent_config import AgentConfig

OutputT = TypeVar("OutputT", bound=BaseModel)
_DEFAULT_MODEL = "gpt-4o-mini"


class PydanticAIClient:
    """Encapsulates model lifecycle and typed run helpers for chatbot agents."""

    def __init__(self, default_config: Optional[AgentConfig] = None):
        self.default_config = default_config or AgentConfig(model_name=config.openai_model)
        self.model = OpenAIChatModel(self.default_config.model_name or _DEFAULT_MODEL)

    @staticmethod
    def _make_system_prompt_reinjector(
        system_prompt: str,
    ) -> Callable[[List[ModelMessage]], List[ModelMessage]]:
        """Build a history processor that guarantees ``system_prompt`` leads request history."""

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
        self,
        output_type: Type[OutputT],
        system_prompt: str,
        *,
        config_override: Optional[AgentConfig] = None,
        temperature: Optional[float] = None,
        sql_validator_fields: Optional[Sequence[str]] = None,
    ) -> Agent[Any, OutputT]:
        """Build a typed agent bound to this client and model settings."""
        effective_config = config_override or self.default_config
        if temperature is not None:
            effective_config = AgentConfig(
                model_name=effective_config.model_name,
                temperature=temperature,
                top_p=effective_config.top_p,
                max_tokens=effective_config.max_tokens,
                frequency_penalty=effective_config.frequency_penalty,
                presence_penalty=effective_config.presence_penalty,
            )

        agent = Agent(
            model=self.model,
            output_type=output_type,
            system_prompt=system_prompt,
            model_settings=effective_config.to_model_settings(),
            history_processors=[self._make_system_prompt_reinjector(system_prompt)],
        )
        if sql_validator_fields:
            self._attach_sql_output_validator(agent, fields=sql_validator_fields)
        return agent

    @staticmethod
    def _attach_sql_output_validator(
        agent: Agent[Any, OutputT],
        *,
        fields: Sequence[str],
    ) -> Agent[Any, OutputT]:
        """Attach SQL output validation with automatic model retry feedback."""

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

    @staticmethod
    def to_message_history(
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> List[ModelMessage]:
        """Convert project message history into Pydantic AI message objects."""
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
            elif role == "system":
                messages.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
            elif role == "assistant":
                messages.append(ModelResponse(parts=[TextPart(content=content)]))
        return messages

    async def run_typed(
        self,
        agent: Agent[Any, OutputT],
        user_message: str,
        *,
        context: str = "LLM call",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> OutputT:
        """Run ``agent`` and return validated output with error translation."""
        history = self.to_message_history(conversation_history)
        try:
            result = await agent.run(user_message, message_history=history)
        except UnexpectedModelBehavior as exc:
            raise RuntimeError(f"{context}: model returned unexpected output — {exc}") from exc
        except ValidationError as exc:
            raise RuntimeError(f"{context}: output failed validation — {exc}") from exc

        return result.output


def build_agent(
    output_type: Type[OutputT],
    system_prompt: str,
    *,
    temperature: float = 0.2,
    model_name: Optional[str] = None,
    sql_validator_fields: Optional[Sequence[str]] = None,
) -> Agent[Any, OutputT]:
    """Backward-compatible helper around ``PydanticAIClient.build_agent``."""
    client = PydanticAIClient(
        default_config=AgentConfig(model_name=model_name or config.openai_model)
    )
    return client.build_agent(
        output_type,
        system_prompt,
        temperature=temperature,
        sql_validator_fields=sql_validator_fields,
    )


def to_message_history(
    conversation_history: Optional[List[Dict[str, str]]],
) -> List[ModelMessage]:
    """Backward-compatible helper around ``PydanticAIClient.to_message_history``."""
    return PydanticAIClient.to_message_history(conversation_history)


async def run_typed(
    agent: Agent[Any, OutputT],
    user_message: str,
    *,
    context: str = "LLM call",
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> OutputT:
    """Backward-compatible helper around ``PydanticAIClient.run_typed``."""
    client = PydanticAIClient()
    return await client.run_typed(
        agent,
        user_message,
        context=context,
        conversation_history=conversation_history,
    )


def attach_sql_output_validator(
    agent: Agent[Any, OutputT],
    *,
    fields: Sequence[str] = ("sql",),
) -> Agent[Any, OutputT]:
    """Backward-compatible SQL validator helper."""
    return PydanticAIClient._attach_sql_output_validator(agent, fields=fields)
