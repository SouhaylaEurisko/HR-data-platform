"""Models for Intent Classifier Agent."""
from pydantic import BaseModel


class IntentClassificationResult(BaseModel):
    """LLM classification output."""
    intent: str  # "chitchat" | "filter" | "aggregation" | "filter_and_aggregation"
    confidence: str  # "high" | "medium" | "low"
    reasoning: str  # short explanation
