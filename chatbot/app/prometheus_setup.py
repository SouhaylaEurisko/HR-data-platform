"""
Prometheus metrics: HTTP RED + custom agent metrics (see ``agent_metrics``).

Expose ``GET /metrics`` for scraping or remote_write to Grafana Cloud Mimir.
"""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def mount_prometheus_metrics(app: FastAPI) -> None:
    """Register default HTTP metrics and expose ``GET /metrics``."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[
            r"/health",
            r"/metrics",
        ],
    ).instrument(
        app,
        metric_namespace="hr_platform",
        metric_subsystem="chatbot",
    ).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["metrics"],
    )
