"""
OpenTelemetry bootstrap for backend service.

 FastAPI auto-instrument
 httpx + SQLAlchemy auto-instrument
 OTLP log export + per-request `request_id` correlation across spans
         and standard ``logging`` records (shipped to Grafana Cloud Loki via OTLP).
"""

from __future__ import annotations

import logging
import os
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as OTLPGrpcLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGrpcSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as OTLPHttpLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .config import engine

_INSTRUMENTED = False

# Per-request id available to log records and spans across async hops.
_REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="-")


def get_current_request_id() -> str:
    """Return the request_id bound to the current context (``-`` outside a request)."""
    return _REQUEST_ID_CTX.get()


class _OtelLogDefaultsFilter(logging.Filter):
    """Fill missing OTel log fields so ``%(otelTraceID)s`` format strings never KeyError.

    OpenTelemetry's own export retry logs use plain ``logging`` without trace
    context, so ``otelTraceID`` / ``otelSpanID`` are absent unless we set them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "otelTraceID"):
            record.otelTraceID = "-"
        if not hasattr(record, "otelSpanID"):
            record.otelSpanID = "-"
        return True


class _RequestIdLogFilter(logging.Filter):
    """Inject ``request_id`` from the context var into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _REQUEST_ID_CTX.get()
        return True


class _RequestIdMiddleware(BaseHTTPMiddleware):
    """Stamp each HTTP request with a UUID and propagate it everywhere."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _REQUEST_ID_CTX.set(rid)
        span = trace.get_current_span()
        if span is not None and span.is_recording():
            span.set_attribute("request_id", rid)
        try:
            response = await call_next(request)
        finally:
            _REQUEST_ID_CTX.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


def _build_resource(default_service_name: str) -> Resource:
    service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)
    return Resource.create({"service.name": service_name})


def _otlp_endpoint_set() -> bool:
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def _otlp_uses_http() -> bool:
    proto = (os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL") or "grpc").strip().lower()
    return proto in ("http/protobuf", "http")


def _build_trace_exporter():
    if not _otlp_endpoint_set():
        return None
    if _otlp_uses_http():
        return OTLPHttpSpanExporter()
    return OTLPGrpcSpanExporter()


def _build_log_exporter():
    if not _otlp_endpoint_set():
        return None
    if _otlp_uses_http():
        return OTLPHttpLogExporter()
    return OTLPGrpcLogExporter()


def _configure_root_logger(otlp_handler: LoggingHandler) -> None:
    """Attach the OTLP handler + request_id filter + a structured stdout handler."""
    root = logging.getLogger()
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)

    root.addFilter(_OtelLogDefaultsFilter())
    root.addFilter(_RequestIdLogFilter())
    root.addHandler(otlp_handler)

    if not any(isinstance(h, logging.StreamHandler) and h is not otlp_handler for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s "
                "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s "
                "request_id=%(request_id)s] %(message)s"
            )
        )
        stream_handler.addFilter(_OtelLogDefaultsFilter())
        stream_handler.addFilter(_RequestIdLogFilter())
        root.addHandler(stream_handler)


def setup_telemetry(app: FastAPI) -> None:
    """Configure global tracing, logging, and instrumentation for the backend."""
    global _INSTRUMENTED
    if _INSTRUMENTED:
        return

    resource = _build_resource("hr-platform-backend")

    tracer_provider = TracerProvider(resource=resource)
    span_exporter = _build_trace_exporter()
    if span_exporter is not None:
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    log_exporter = _build_log_exporter()
    if log_exporter is not None:
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    otlp_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    _configure_root_logger(otlp_handler)
    LoggingInstrumentor().instrument(set_logging_format=False)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)

    app.add_middleware(_RequestIdMiddleware)

    _INSTRUMENTED = True
