"""Typed configuration object for LLM agent settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for Pydantic AI agent behavior."""

    model_name: str = "gpt-4o-mini"
    temperature: float = 0.2
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None

    def to_model_settings(self) -> Dict[str, Any]:
        """Return only non-None settings accepted by model providers."""
        return {
            key: value
            for key, value in asdict(self).items()
            if key != "model_name" and value is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Compatibility alias used by upcoming client refactor."""
        return self.to_model_settings()
