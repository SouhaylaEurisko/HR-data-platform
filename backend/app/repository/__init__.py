"""Data access layer — SQLAlchemy query and persistence logic."""

from . import analytics_repository
from . import auth_repository
from . import candidate_stage_comments_repository
from . import candidates_repository
from . import column_normalizer_repository
from . import custom_fields_repository
from . import import_repository
from . import lookups_repository
from . import resume_repository

__all__ = [
    "analytics_repository",
    "auth_repository",
    "candidate_stage_comments_repository",
    "candidates_repository",
    "column_normalizer_repository",
    "custom_fields_repository",
    "import_repository",
    "lookups_repository",
    "resume_repository",
]
