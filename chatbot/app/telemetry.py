"""
OpenTelemetry bootstrap for chatbot service.

 FastAPI auto-instrument
 httpx + SQLAlchemy auto-instrument
 Logfire + Pydantic-AI (Logfire must own the global Tracer/Logger providers once)
 OTLP export + request_id on logs
"""

from __future__ import annotations

import logging
import os
import uuid
from contextvars import ContextVar
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import get_logger_provider, set_logger_provider
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

from .config import config, engine

_INSTRUMENTED = False

_REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="-")


def get_current_request_id() -> str:
    return _REQUEST_ID_CTX.get()


def set_current_request_id(request_id: str) -> None:
    _REQUEST_ID_CTX.set(request_id)
    span = trace.get_current_span()
    if span is not None and span.is_recording():
        span.set_attribute("request_id", request_id)


class _OtelLogDefaultsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "otelTraceID"):
            record.otelTraceID = "-"
        if not hasattr(record, "otelSpanID"):
            record.otelSpanID = "-"
        return True


class _RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _REQUEST_ID_CTX.get()
        return True


class _RequestIdMiddleware(BaseHTTPMiddleware):
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


def _configure_logfire_globals(
    service_name: str,
    *,
    span_exporter,
    log_exporter,
) -> bool:
    """Configure Logfire first so it owns global OTel providers (no override warnings).

    Returns True if Logfire configured successfully.
    """
    try:
        import logfire
        from logfire import AdvancedOptions
    except ImportError as exc:
        logging.getLogger(__name__).warning(
            "Logfire is not available (%s). Install `logfire` and OpenTelemetry 1.39.x "
            "(see chatbot/requirements.txt). Falling back to manual TracerProvider.",
            exc,
        )
        return False

    additional_span_processors = []
    if span_exporter is not None:
        additional_span_processors.append(BatchSpanProcessor(span_exporter))

    log_record_processors = []
    if log_exporter is not None:
        log_record_processors.append(BatchLogRecordProcessor(log_exporter))

    advanced = AdvancedOptions(
        log_record_processors=tuple(log_record_processors),
    )

    lf_token = (config.logfire_token or "").strip() or None
    configure_kwargs: dict = {
        "send_to_logfire": bool(lf_token),
        "service_name": service_name,
        "console": False,
        "advanced": advanced,
    }
    if lf_token:
        configure_kwargs["token"] = lf_token
    if additional_span_processors:
        configure_kwargs["additional_span_processors"] = additional_span_processors

    logfire.configure(**configure_kwargs)
    try:
        logfire.instrument_pydantic_ai()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("Failed to instrument Pydantic-AI via logfire: %s", exc)
    return True


def setup_telemetry(app: FastAPI) -> None:
    """Configure global tracing, logging, and instrumentation for the chatbot."""
    global _INSTRUMENTED
    if _INSTRUMENTED:
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "hr-platform-chatbot")
    span_exporter = _build_trace_exporter()
    log_exporter = _build_log_exporter()

    if not _configure_logfire_globals(
        service_name,
        span_exporter=span_exporter,
        log_exporter=log_exporter,
    ):
        resource = _build_resource(service_name)
        tracer_provider = TracerProvider(resource=resource)
        if span_exporter is not None:
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        logger_provider = LoggerProvider(resource=resource)
        if log_exporter is not None:
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)

    otlp_handler = LoggingHandler(level=logging.INFO, logger_provider=get_logger_provider())
    _configure_root_logger(otlp_handler)
    LoggingInstrumentor().instrument(set_logging_format=False)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)

    app.add_middleware(_RequestIdMiddleware)

    _INSTRUMENTED = True
