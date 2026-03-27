"""
Application configuration — reads all environment variables.
Use the `config` instance to access any environment variable throughout the app.
"""

import os
from typing import List
from dotenv import load_dotenv


class Config:
    """
    Centralized configuration class that reads from environment variables.
    Access any environment variable via the global `config` instance.
    """
    
    def __init__(self):
        """Load environment variables from .env file."""
        load_dotenv()
    
    # ──────────────────────────────────────────────
    # Database Configuration
    # ──────────────────────────────────────────────
    
    @property
    def database_url(self) -> str:
        """Database connection URL (PostgreSQL required)."""
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL environment variable is required. "
                "Please set it to a PostgreSQL connection string, e.g.: "
                "postgresql://user:password@host:5432/database"
            )
        if not url.startswith("postgresql"):
            raise ValueError(
                f"DATABASE_URL must point to PostgreSQL, not {url.split('://')[0] if '://' in url else 'unknown'}. "
                "Please set DATABASE_URL to a PostgreSQL connection string."
            )
        return url
    
    # ──────────────────────────────────────────────
    # OpenAI Configuration
    # ──────────────────────────────────────────────
    
    @property
    def openai_api_key(self) -> str:
        """OpenAI API key (required)."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        return key
    
    @property
    def openai_model(self) -> str:
        """OpenAI model name."""
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    # ──────────────────────────────────────────────
    # Server Configuration
    # ──────────────────────────────────────────────
    
    @property
    def server_host(self) -> str:
        """Server host address."""
        return os.getenv("SERVER_HOST", "0.0.0.0")
    
    @property
    def server_port(self) -> int:
        """Server port number."""
        return int(os.getenv("SERVER_PORT", "8000"))
    
    # ──────────────────────────────────────────────
    # JWT Configuration
    # ──────────────────────────────────────────────
    
    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key for token signing."""
        key = os.getenv("JWT_SECRET_KEY")
        if not key:
            raise RuntimeError("JWT_SECRET_KEY environment variable is required.")
        return key
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm."""
        return os.getenv("JWT_ALGORITHM", "HS256")
    
    @property
    def jwt_expire_minutes(self) -> int:
        """JWT token expiration in minutes."""
        return int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    
    # ──────────────────────────────────────────────
    # Chatbot Service Configuration
    # ──────────────────────────────────────────────
    
    @property
    def chatbot_service_url(self) -> str:
        """Chatbot service base URL."""
        return os.getenv("CHATBOT_SERVICE_URL")
    
    # ──────────────────────────────────────────────
    # CORS Configuration
    # ──────────────────────────────────────────────
    
    @property
    def cors_origins(self) -> List[str]:
        """Allowed CORS origins (comma-separated or space-separated)."""
        origins_str = os.getenv("CORS_ORIGINS")
        if not origins_str:
            # Default origins if not set
            return [
                "*",
            ]
        # Support both comma and space separation
        # origins = origins_str.replace(",", " ").split()
        origins = ["*"]
        return [origin.strip() for origin in origins if origin.strip()]


# ──────────────────────────────────────────────
# Global Configuration Instance
# ──────────────────────────────────────────────

config = Config()
