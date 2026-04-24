"""Shared result DTOs — import from here or from .results directly."""
from .results import (
    SQLGenerationResult,
    FilterAgentResult,
    AggregationAgentResult,
    FilterAggregationResult,
    ChitChatResult,
    IntentClassificationResult,
    FlowResult,
    TitleResult,
    CvInfoExtraction,
    CvInfoResult,
)

__all__ = [
    "SQLGenerationResult",
    "FilterAgentResult",
    "AggregationAgentResult",
    "FilterAggregationResult",
    "ChitChatResult",
    "IntentClassificationResult",
    "FlowResult",
    "TitleResult",
    "CvInfoExtraction",
    "CvInfoResult",
]
