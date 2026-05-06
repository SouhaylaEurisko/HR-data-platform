"""
Inbound HTTP audit lines for Loki (``app.http.access``).

Do not pass ``otelTraceID`` / ``otelSpanID`` in ``logging`` ``extra``: OpenTelemetry's
``LoggingInstrumentor`` record factory always sets those first, and Python raises
``KeyError: Attempt to overwrite 'otelTraceID' in LogRecord`` if ``extra`` tries to
replace them. Correlation comes from the active span at emit time + ``_RequestIdLogFilter``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("app.http.access")


def log_inbound_request(
    *,
    method: str,
    path: str,
    query: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Log one line per handled HTTP request (excludes paths skipped by middleware)."""
    path_part = f"{path}?{query}" if query else path
    logger.info(
        "Inbound HTTP %s %s -> %s (%.2f ms)",
        method,
        path_part,
        status_code,
        duration_ms,
    )
