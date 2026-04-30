"""
Prometheus metrics: HTTP RED via prometheus-fastapi-instrumentator.

Expose ``/metrics`` in Prometheus text format. For Grafana Cloud, scrape this
endpoint with Grafana Alloy / Agent and ``remote_write`` to Mimir, or use a
hosted scrape target if your deployment exposes the port.
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
        metric_subsystem="backend",
    ).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["metrics"],
    )
