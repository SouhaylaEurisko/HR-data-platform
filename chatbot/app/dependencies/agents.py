"""Dependency providers for Pydantic AI client and chatbot agents."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Any

from fastapi import Depends
from pydantic_ai import Agent

from ..agents.aggregation_agent import AggregationAgent
from ..agents.aggregation_agent.aggregation_service import AggregationService
from ..agents.aggregation_agent.prompts import AGGREGATION_SQL_PROMPT, AGGREGATION_SUMMARY_PROMPT
from ..agents.candidate_comparison_agent import CandidateComparisonAgent
from ..agents.candidate_comparison_agent.prompts import (
    COMPARISON_DECIDE_PROMPT,
    COMPARISON_EXTRACT_PROMPT,
)
from ..agents.chit_chat_agent import ChitChatAgent
from ..agents.chit_chat_agent.prompts import CHITCHAT_PROMPT
from ..agents.constants import (
    CHIT_CHAT_CONFIG,
    CLASSIFICATION_CONFIG,
    COMPARISON_DECISION_CONFIG,
    SQL_GENERATION_CONFIG,
    SUMMARY_CONFIG,
    TITLE_GENERATION_CONFIG,
)
from ..agents.cv_info_agent import CvInfoAgent
from ..agents.cv_info_agent.prompts import (
    CV_INFO_EXTRACT_PROMPT,
    CV_INFO_SQL_PROMPT,
    CV_INFO_SUMMARY_PROMPT,
)
from ..agents.dtos import (
    AggregationSummaryResult,
    ChitChatResult,
    ComparisonDecision,
    ComparisonExtraction,
    CvInfoExtraction,
    CvInfoSummaryResult,
    FilterAggSummaryResult,
    FilterAggregationSQLResult,
    FilterSummaryResult,
    HrFeedbackExtraction,
    IntentClassificationResult,
    SQLGenerationResult,
    TitleResult,
)
from ..agents.filter_agent import FilterAgent
from ..agents.filter_agent.filter_service import FilterService
from ..agents.filter_agent.prompts import FILTER_SQL_PROMPT, FILTER_SUMMARY_PROMPT
from ..agents.filter_aggregation_agent import FilterAggregationAgent
from ..agents.filter_aggregation_agent.filter_aggregation_service import (
    FilterAggregationService,
)
from ..agents.filter_aggregation_agent.prompts import (
    FILTER_AGG_SQL_PROMPT,
    FILTER_AGG_SUMMARY_PROMPT,
)
from ..agents.flow_agent import FlowAgent
from ..agents.hr_feedback_agent import HrFeedbackAgent
from ..agents.hr_feedback_agent.prompts import HR_FEEDBACK_EXTRACT_PROMPT
from ..agents.intent_classifier_agent import IntentClassifierAgent
from ..agents.intent_classifier_agent.prompts import INTENT_CLASSIFICATION_PROMPT
from ..agents.title_agent import TitleAgent
from ..agents.title_agent.prompts import TITLE_GENERATION_PROMPT
from ..config import config
from ..config.agent_config import AgentConfig
from ..utils.pydantic_ai_client import PydanticAIClient


def _with_client_model(base: AgentConfig, client: PydanticAIClient) -> AgentConfig:
    return replace(base, model_name=client.default_config.model_name)


@lru_cache(maxsize=1)
def get_pydantic_ai_client() -> PydanticAIClient:
    """Singleton Pydantic AI client reused across all provider functions."""
    return PydanticAIClient(default_config=AgentConfig(model_name=config.openai_model))


def get_filter_sql_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, SQLGenerationResult]:
    return client.build_agent(
        SQLGenerationResult,
        FILTER_SQL_PROMPT,
        config_override=_with_client_model(SQL_GENERATION_CONFIG, client),
        sql_validator_fields=("sql",),
    )


def get_filter_summary_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, FilterSummaryResult]:
    return client.build_agent(
        FilterSummaryResult,
        FILTER_SUMMARY_PROMPT,
        config_override=_with_client_model(SUMMARY_CONFIG, client),
    )


def get_aggregation_sql_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, SQLGenerationResult]:
    return client.build_agent(
        SQLGenerationResult,
        AGGREGATION_SQL_PROMPT,
        config_override=_with_client_model(SQL_GENERATION_CONFIG, client),
        sql_validator_fields=("sql",),
    )


def get_aggregation_summary_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, AggregationSummaryResult]:
    return client.build_agent(
        AggregationSummaryResult,
        AGGREGATION_SUMMARY_PROMPT,
        config_override=_with_client_model(SUMMARY_CONFIG, client),
    )


def get_filter_aggregation_sql_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, FilterAggregationSQLResult]:
    return client.build_agent(
        FilterAggregationSQLResult,
        FILTER_AGG_SQL_PROMPT,
        config_override=_with_client_model(SQL_GENERATION_CONFIG, client),
        sql_validator_fields=("filter_sql", "aggregation_sql"),
    )


def get_filter_aggregation_summary_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, FilterAggSummaryResult]:
    return client.build_agent(
        FilterAggSummaryResult,
        FILTER_AGG_SUMMARY_PROMPT,
        config_override=_with_client_model(SUMMARY_CONFIG, client),
    )


def get_cv_info_extract_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, CvInfoExtraction]:
    return client.build_agent(
        CvInfoExtraction,
        CV_INFO_EXTRACT_PROMPT,
        config_override=_with_client_model(CLASSIFICATION_CONFIG, client),
    )


def get_cv_info_sql_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, SQLGenerationResult]:
    return client.build_agent(
        SQLGenerationResult,
        CV_INFO_SQL_PROMPT,
        config_override=_with_client_model(SQL_GENERATION_CONFIG, client),
        sql_validator_fields=("sql",),
    )


def get_cv_info_summary_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, CvInfoSummaryResult]:
    return client.build_agent(
        CvInfoSummaryResult,
        CV_INFO_SUMMARY_PROMPT,
        config_override=_with_client_model(SUMMARY_CONFIG, client),
    )


def get_intent_classifier_llm_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, IntentClassificationResult]:
    return client.build_agent(
        IntentClassificationResult,
        INTENT_CLASSIFICATION_PROMPT,
        config_override=_with_client_model(CLASSIFICATION_CONFIG, client),
    )


def get_chitchat_llm_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, ChitChatResult]:
    return client.build_agent(
        ChitChatResult,
        CHITCHAT_PROMPT,
        config_override=_with_client_model(CHIT_CHAT_CONFIG, client),
    )


def get_hr_feedback_extract_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, HrFeedbackExtraction]:
    return client.build_agent(
        HrFeedbackExtraction,
        HR_FEEDBACK_EXTRACT_PROMPT,
        config_override=_with_client_model(CLASSIFICATION_CONFIG, client),
    )


def get_comparison_extract_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, ComparisonExtraction]:
    return client.build_agent(
        ComparisonExtraction,
        COMPARISON_EXTRACT_PROMPT,
        config_override=_with_client_model(CLASSIFICATION_CONFIG, client),
    )


def get_comparison_decide_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, ComparisonDecision]:
    return client.build_agent(
        ComparisonDecision,
        COMPARISON_DECIDE_PROMPT,
        config_override=_with_client_model(COMPARISON_DECISION_CONFIG, client),
    )


def get_title_llm_agent(
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> Agent[Any, TitleResult]:
    return client.build_agent(
        TitleResult,
        TITLE_GENERATION_PROMPT,
        config_override=_with_client_model(TITLE_GENERATION_CONFIG, client),
    )


def get_filter_service(
    sql_agent: Agent[Any, SQLGenerationResult] = Depends(get_filter_sql_agent),
    summary_agent: Agent[Any, FilterSummaryResult] = Depends(get_filter_summary_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> FilterService:
    return FilterService(sql_agent=sql_agent, summary_agent=summary_agent, ai_client=client)


def get_aggregation_service(
    sql_agent: Agent[Any, SQLGenerationResult] = Depends(get_aggregation_sql_agent),
    summary_agent: Agent[Any, AggregationSummaryResult] = Depends(
        get_aggregation_summary_agent
    ),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> AggregationService:
    return AggregationService(
        sql_agent=sql_agent,
        summary_agent=summary_agent,
        ai_client=client,
    )


def get_filter_aggregation_service(
    sql_agent: Agent[Any, FilterAggregationSQLResult] = Depends(
        get_filter_aggregation_sql_agent
    ),
    summary_agent: Agent[Any, FilterAggSummaryResult] = Depends(
        get_filter_aggregation_summary_agent
    ),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> FilterAggregationService:
    return FilterAggregationService(
        sql_agent=sql_agent,
        summary_agent=summary_agent,
        ai_client=client,
    )


def get_cv_info_agent(
    extract_agent: Agent[Any, CvInfoExtraction] = Depends(get_cv_info_extract_agent),
    sql_agent: Agent[Any, SQLGenerationResult] = Depends(get_cv_info_sql_agent),
    summary_agent: Agent[Any, CvInfoSummaryResult] = Depends(get_cv_info_summary_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> CvInfoAgent:
    return CvInfoAgent(
        extract_agent=extract_agent,
        sql_agent=sql_agent,
        summary_agent=summary_agent,
        ai_client=client,
    )


def get_intent_classifier_agent(
    agent: Agent[Any, IntentClassificationResult] = Depends(get_intent_classifier_llm_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> IntentClassifierAgent:
    return IntentClassifierAgent(agent=agent, ai_client=client)


def get_chit_chat_agent(
    agent: Agent[Any, ChitChatResult] = Depends(get_chitchat_llm_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> ChitChatAgent:
    return ChitChatAgent(agent=agent, ai_client=client)


def get_hr_feedback_agent(
    agent: Agent[Any, HrFeedbackExtraction] = Depends(get_hr_feedback_extract_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> HrFeedbackAgent:
    return HrFeedbackAgent(agent=agent, ai_client=client)


def get_candidate_comparison_agent(
    extract_agent: Agent[Any, ComparisonExtraction] = Depends(get_comparison_extract_agent),
    decide_agent: Agent[Any, ComparisonDecision] = Depends(get_comparison_decide_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> CandidateComparisonAgent:
    return CandidateComparisonAgent(
        extract_agent=extract_agent,
        decide_agent=decide_agent,
        ai_client=client,
    )


def get_title_agent(
    agent: Agent[Any, TitleResult] = Depends(get_title_llm_agent),
    client: PydanticAIClient = Depends(get_pydantic_ai_client),
) -> TitleAgent:
    return TitleAgent(agent=agent, ai_client=client)


def get_filter_agent(
    service: FilterService = Depends(get_filter_service),
) -> FilterAgent:
    return FilterAgent(service=service)


def get_aggregation_agent(
    service: AggregationService = Depends(get_aggregation_service),
) -> AggregationAgent:
    return AggregationAgent(service=service)


def get_filter_aggregation_agent(
    service: FilterAggregationService = Depends(get_filter_aggregation_service),
) -> FilterAggregationAgent:
    return FilterAggregationAgent(service=service)


def get_flow_agent(
    classifier: IntentClassifierAgent = Depends(get_intent_classifier_agent),
    chitchat: ChitChatAgent = Depends(get_chit_chat_agent),
    filter_agent: FilterAgent = Depends(get_filter_agent),
    aggregation: AggregationAgent = Depends(get_aggregation_agent),
    filter_agg: FilterAggregationAgent = Depends(get_filter_aggregation_agent),
    hr_feedback: HrFeedbackAgent = Depends(get_hr_feedback_agent),
    candidate_comparison: CandidateComparisonAgent = Depends(get_candidate_comparison_agent),
    cv_info: CvInfoAgent = Depends(get_cv_info_agent),
) -> FlowAgent:
    return FlowAgent(
        classifier=classifier,
        chitchat=chitchat,
        filter_agent=filter_agent,
        aggregation=aggregation,
        filter_agg=filter_agg,
        hr_feedback=hr_feedback,
        candidate_comparison=candidate_comparison,
        cv_info=cv_info,
    )
