"""Agent temperature presets and reusable configuration variants."""

from __future__ import annotations

from ..config.agent_config import AgentConfig

# Temperature presets
TEMPERATURE_DETERMINISTIC = 0.2  # SQL generation, extraction, classification
TEMPERATURE_BALANCED = 0.4  # summaries
TEMPERATURE_ANALYTICAL = 0.3  # comparison decisions
TEMPERATURE_CREATIVE = 0.88  # chit-chat
TEMPERATURE_TITLE = 0.5  # short title generation

# Standard configs for upcoming class-based PydanticAI client integration.
DEFAULT_AGENT_CONFIG = AgentConfig()
SQL_GENERATION_CONFIG = AgentConfig(
    temperature=TEMPERATURE_DETERMINISTIC,
    top_p=0.95,
)
SUMMARY_CONFIG = AgentConfig(
    temperature=TEMPERATURE_BALANCED,
    top_p=0.95,
)
CLASSIFICATION_CONFIG = AgentConfig(
    temperature=TEMPERATURE_DETERMINISTIC,
    top_p=0.95,
)
COMPARISON_DECISION_CONFIG = AgentConfig(
    temperature=TEMPERATURE_ANALYTICAL,
    top_p=0.95,
)
CHIT_CHAT_CONFIG = AgentConfig(
    temperature=TEMPERATURE_CREATIVE,
    top_p=1.0,
)
TITLE_GENERATION_CONFIG = AgentConfig(
    temperature=TEMPERATURE_TITLE,
)
