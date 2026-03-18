"""
Configuration for chatbot service.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration loaded from environment variables."""
    
    # Server configuration
    server_host: str = os.getenv("SERVER_HOST")
    server_port: int = int(os.getenv("SERVER_PORT"))
    
    # Database configuration
    # PostgreSQL connection string format: postgresql://user:password@host:port/database
    database_url: str = os.getenv(
        "DATABASE_URL"
    )
    
    # OpenAI configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL")
    
    # CORS configuration
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS"
    ).split(",")


# Global config instance
config = Config()
