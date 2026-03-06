import os
from dotenv import load_dotenv


from pydantic import BaseModel


class Settings(BaseModel):
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"


def get_settings() -> Settings:
    """
    Load settings from environment variables.

    Required:
    - OPENAI_API_KEY
    Optional:
    - OPENAI_MODEL (defaults to gpt-4.1-mini)
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    return Settings(openai_api_key=api_key, openai_model=model)


