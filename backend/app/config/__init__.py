"""
Configuration package — settings, database, and authentication.
"""

from .config import config, Config
from .settings import Settings, get_settings
from .database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    init_db,
)

__all__ = [
    # Config instance (main way to access env vars)
    "config",
    "Config",
    # Settings (legacy, for backward compatibility)
    "Settings",
    "get_settings",
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
]