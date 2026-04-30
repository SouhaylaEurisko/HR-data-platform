"""
Custom Prometheus metrics for the chatbot agent pipeline (RED per routed agent).

Used by ``FlowAgent``; HTTP-level RED comes from ``prometheus_setup`` (instrumentator).
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from prometheus_client import Counter, Histogram

_NS = "hr_platform"

_INTENT_CLASSIFICATION_RUNS = Counter(
    "classification_runs_total",
    "Intent classifier invocations",
    ["status"],
    namespace=_NS,
    subsystem="chatbot_intent",
)

_INTENT_CLASSIFICATION_LATENCY = Histogram(
    "classification_latency_seconds",
    "Wall time for intent classification (LLM call)",
    namespace=_NS,
    subsystem="chatbot_intent",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

_AGENT_RUNS = Counter(
    "runs_total",
    "Routed agent executions",
    ["agent", "status"],
    namespace=_NS,
    subsystem="chatbot_agent",
)

_AGENT_LATENCY = Histogram(
    "latency_seconds",
    "Wall time inside a routed agent handler",
    ["agent"],
    namespace=_NS,
    subsystem="chatbot_agent",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)


@asynccontextmanager
async def observe_intent_classification() -> AsyncIterator[None]:
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except BaseException:
        status = "error"
        raise
    finally:
        _INTENT_CLASSIFICATION_RUNS.labels(status=status).inc()
        _INTENT_CLASSIFICATION_LATENCY.observe(time.perf_counter() - start)


@asynccontextmanager
async def observe_routed_agent(agent: str) -> AsyncIterator[None]:
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except BaseException:
        status = "error"
        raise
    finally:
        _AGENT_RUNS.labels(agent=agent, status=status).inc()
        _AGENT_LATENCY.labels(agent=agent).observe(time.perf_counter() - start)
