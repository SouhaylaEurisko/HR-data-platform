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
import time
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
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import config, engine

_INSTRUMENTED = False

_ROOT_OTLP_HANDLER: LoggingHandler | None = None
_ROOT_STREAM_HANDLER: logging.StreamHandler | None = None

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


_ACCESS_LOG_SKIP_PATHS = frozenset({"/health", "/metrics"})


def _asgi_header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or []:
        if key.lower() == name.lower():
            return value.decode("latin-1")
    return None


class _InboundRequestLogMiddleware:
    """Pure ASGI middleware: wraps every HTTP request (no BaseHTTPMiddleware gaps).

    Logs with the ``httpx`` logger using the same ``HTTP Request:`` line shape as outbound
    httpx calls so Grafana/Loki OTLP pipelines attribute them identically to working logs.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path in _ACCESS_LOG_SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        raw_rid = _asgi_header(scope, b"x-request-id")
        rid = raw_rid if raw_rid else str(uuid.uuid4())
        token = _REQUEST_ID_CTX.set(rid)
        start = time.perf_counter()
        status_holder: dict[str, int | None] = {"code": None}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                new_msg = dict(message)
                headers = list(new_msg.get("headers") or [])
                if not any(hk.lower() == b"x-request-id" for hk, _ in headers):
                    headers.append((b"x-request-id", rid.encode("latin-1")))
                new_msg["headers"] = headers
                await send(new_msg)
                return
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                duration_ms = (time.perf_counter() - start) * 1000
                method = scope.get("method", "?")
                qs = scope.get("query_string", b"").decode("latin-1")
                path_display = f"{path}?{qs}" if qs else path
                code = status_holder["code"] if status_holder["code"] is not None else 0

                span = trace.get_current_span()
                if span is not None and span.is_recording():
                    span.set_attribute("request_id", rid)
                    span.set_attribute("http.response.status_code", code)
                    span.set_attribute("http.server.request.duration_ms", round(duration_ms, 3))

                if _ROOT_OTLP_HANDLER is not None and _ROOT_OTLP_HANDLER not in logging.getLogger().handlers:
                    reattach_root_log_handlers()

                logging.getLogger("httpx").info(
                    'HTTP Request: %s %s "%s"',
                    method,
                    path_display,
                    f"HTTP/1.1 {code}",
                )
            finally:
                _REQUEST_ID_CTX.reset(token)


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
    global _ROOT_OTLP_HANDLER, _ROOT_STREAM_HANDLER
    _ROOT_OTLP_HANDLER = otlp_handler

    root = logging.getLogger()
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)

    if not any(isinstance(f, _OtelLogDefaultsFilter) for f in root.filters):
        root.addFilter(_OtelLogDefaultsFilter())
    if not any(isinstance(f, _RequestIdLogFilter) for f in root.filters):
        root.addFilter(_RequestIdLogFilter())
    if otlp_handler not in root.handlers:
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
        _ROOT_STREAM_HANDLER = stream_handler
    elif _ROOT_STREAM_HANDLER is None:
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler) and h is not otlp_handler:
                _ROOT_STREAM_HANDLER = h
                break


def reattach_root_log_handlers() -> None:
    """Call from FastAPI startup: uvicorn replaces logging config after import and drops OTLP handlers."""
    global _ROOT_OTLP_HANDLER, _ROOT_STREAM_HANDLER
    if _ROOT_OTLP_HANDLER is None:
        return
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if _ROOT_OTLP_HANDLER not in root.handlers:
        root.addHandler(_ROOT_OTLP_HANDLER)
    if _ROOT_STREAM_HANDLER is not None and _ROOT_STREAM_HANDLER not in root.handlers:
        root.addHandler(_ROOT_STREAM_HANDLER)
    if not any(isinstance(f, _OtelLogDefaultsFilter) for f in root.filters):
        root.addFilter(_OtelLogDefaultsFilter())
    if not any(isinstance(f, _RequestIdLogFilter) for f in root.filters):
        root.addFilter(_RequestIdLogFilter())


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

    app.add_middleware(_InboundRequestLogMiddleware)

    _INSTRUMENTED = True
