"""
Application settings and configuration (legacy compatibility).
Uses the global config instance internally.
"""

from pydantic import BaseModel
from .config import config


class Settings(BaseModel):
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"


def get_settings() -> Settings:
    """
    Load settings from environment variables (uses global config instance).

    Required:
    - OPENAI_API_KEY
    Optional:
    - OPENAI_MODEL (defaults to gpt-4.1-mini)
    
    Note: For new code, use `from app.config import config` and access
    `config.openai_api_key` and `config.openai_model` directly.
    """
    return Settings(
        openai_api_key=config.openai_api_key,
        openai_model=config.openai_model
    )
