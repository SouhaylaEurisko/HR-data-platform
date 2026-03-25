"""Models for Intent Classifier Agent."""
from pydantic import BaseModel


class IntentClassificationResult(BaseModel):
    """LLM classification output."""
    intent: str  # chitchat | filter | aggregation | filter_and_aggregation | hr_feedback | candidate_comparison | cv_info
    confidence: str  # "high" | "medium" | "low"
    reasoning: str  # short explanation
