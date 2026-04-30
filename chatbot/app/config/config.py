"""Configuration for chatbot service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Config(BaseSettings):
    """Application settings loaded from environment variables."""

    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)

    database_url: str

    openai_api_key: str
    openai_model: str = Field(default="gpt-4o-mini")

    logfire_token: str | None = Field(
        default=None,
        description="Pydantic Logfire project write token; loaded from LOGFIRE_TOKEN in env or chatbot/.env",
    )

    cors_origins: Annotated[List[str], NoDecode] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> List[str]:
        if value is None:
            return ["*"]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    decoded = json.loads(stripped)
                except json.JSONDecodeError:
                    decoded = None
                if isinstance(decoded, list):
                    return [str(item).strip() for item in decoded if str(item).strip()] or ["*"]
            parsed = [item.strip() for item in value.split(",") if item.strip()]
            return parsed or ["*"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()] or ["*"]
        return ["*"]


config = Config()
