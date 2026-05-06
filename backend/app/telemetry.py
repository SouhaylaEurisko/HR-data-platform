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
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.trace import SpanKind, Status, StatusCode, format_span_id, format_trace_id
from starlette.types import ASGIApp, Message, Receive, Scope, Send
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

from .config import engine

_INSTRUMENTED = False

# Kept so we can re-attach after uvicorn/logging.config replaces root handlers at startup.
_ROOT_OTLP_HANDLER: LoggingHandler | None = None
_ROOT_STREAM_HANDLER: logging.StreamHandler | None = None

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
        span = trace.get_current_span()
        ctx = span.get_span_context() if span is not None else None
        if ctx is not None and ctx.is_valid:
            # Keep log correlation correct even if the log record factory prefilled "0".
            record.otelTraceID = format_trace_id(ctx.trace_id)
            record.otelSpanID = format_span_id(ctx.span_id)
        else:
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


_ACCESS_LOG_SKIP_PATHS = frozenset({"/health", "/metrics"})


def _asgi_header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or []:
        if key.lower() == name.lower():
            return value.decode("latin-1")
    return None


class _InboundRequestLogMiddleware:
    """Pure ASGI middleware: one structured line per inbound HTTP request.

    Register this **after** CORS and Prometheus so it sits outermost among app middleware:
    then every request (including CORS preflight) flows through this wrapper and
    ``send_wrapper`` still sees the response.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._tracer = trace.get_tracer("hr-platform-backend.inbound")

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

        method = scope.get("method", "?")
        qs = scope.get("query_string", b"").decode("latin-1")
        span_name = f"{method} {path or '/'}"
        with self._tracer.start_as_current_span(span_name, kind=SpanKind.SERVER) as span:
            if span is not None and span.is_recording():
                span.set_attribute("request_id", rid)
                span.set_attribute("http.request.method", method)
                span.set_attribute("url.path", path)
                if qs:
                    span.set_attribute("url.query", qs)
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                try:
                    duration_ms = (time.perf_counter() - start) * 1000
                    code = status_holder["code"] if status_holder["code"] is not None else 0

                    if span is not None and span.is_recording():
                        span.set_attribute("http.response.status_code", code)
                        span.set_attribute("http.server.request.duration_ms", round(duration_ms, 3))
                        if int(code) >= 500:
                            span.set_status(Status(StatusCode.ERROR))

                    if _ROOT_OTLP_HANDLER is not None and _ROOT_OTLP_HANDLER not in logging.getLogger().handlers:
                        reattach_root_log_handlers()

                    # Dedicated access logger (not ``httpx``) so Loki distinguishes inbound API lines
                    # from outbound proxy/client calls; correlation via current span + request_id ctx var.
                    from .observability.request_audit import log_inbound_request

                    log_inbound_request(
                        method=method,
                        path=path,
                        query=qs,
                        status_code=int(code),
                        duration_ms=duration_ms,
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


def _configure_correlation_child_loggers() -> None:
    """Attach correlation filters to loggers that emit under the root but are not ``logging.root``.

    Python only runs ``Logger.filter`` on the logger that emitted the record, not on parents when
    propagating to shared handlers — without this, ``app.http.access`` / ``httpx`` lines can miss
    ``request_id`` in formatters and OTLP.
    """
    for name in ("app.http.access", "httpx"):
        log = logging.getLogger(name)
        if log.level == logging.NOTSET or log.level > logging.INFO:
            log.setLevel(logging.INFO)
        if not any(isinstance(f, _OtelLogDefaultsFilter) for f in log.filters):
            log.addFilter(_OtelLogDefaultsFilter())
        if not any(isinstance(f, _RequestIdLogFilter) for f in log.filters):
            log.addFilter(_RequestIdLogFilter())


def _configure_root_logger(otlp_handler: LoggingHandler) -> None:
    """Attach the OTLP handler + request_id filter + a structured stdout handler."""
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
        # Handler filters run for child loggers; root ``Logger.filter`` does not.
        if not any(isinstance(f, _OtelLogDefaultsFilter) for f in otlp_handler.filters):
            otlp_handler.addFilter(_OtelLogDefaultsFilter())
        if not any(isinstance(f, _RequestIdLogFilter) for f in otlp_handler.filters):
            otlp_handler.addFilter(_RequestIdLogFilter())
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

    _configure_correlation_child_loggers()


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

    _configure_correlation_child_loggers()


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

    _INSTRUMENTED = True


def add_inbound_access_middleware(app: FastAPI) -> None:
    """Append inbound access logging (must be last ``add_middleware`` so it wraps CORS/Prometheus)."""
    app.add_middleware(_InboundRequestLogMiddleware)
