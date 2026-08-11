from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, cast

import structlog
from structlog.typing import EventDict, Processor
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import Status, StatusCode

_configured = False

_SENSITIVE_FIELD_PARTS = {
    "accesstoken",
    "appsecret",
    "authorization",
    "bindingticket",
    "identitypepper",
    "openid",
    "password",
    "sessionkey",
}
_REDACTED = "[REDACTED]"


def _is_sensitive_field(name: str) -> bool:
    normalized = "".join(character for character in name.lower() if character.isalnum())
    return any(part in normalized for part in _SENSITIVE_FIELD_PARTS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_sensitive_field(str(key)) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def redact_sensitive_fields(
    _logger: Any, _method_name: str, event_dict: EventDict
) -> EventDict:
    return cast(EventDict, _redact_value(event_dict))

def configure_observability() -> None:
    global _configured
    if _configured:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    log_format = os.getenv("LOG_FORMAT", "console" if os.getenv("APP_ENV", "development") == "development" else "json")
    renderer = structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer(colors=False)
    structlog.configure(
        processors=[
            *processors,
            redact_sensitive_fields,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    if os.getenv("OTEL_ENABLED", "true").lower() in {"1", "true", "yes"}:
        sample_ratio = min(1.0, max(0.0, float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))))
        provider = TracerProvider(resource=Resource.create({
            "service.name": os.getenv("OTEL_SERVICE_NAME", os.getenv("APP_NAME", "yoga-sys-backend")),
            "deployment.environment": os.getenv("APP_ENV", "development"),
        }), sampler=TraceIdRatioBased(sample_ratio))
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
    _configured = True

def get_logger():
    return structlog.get_logger()

def get_tracer():
    return trace.get_tracer("yoga-sys-backend")

@contextmanager
def business_span(name: str, **attributes: Any) -> Iterator[Any]:
    with get_tracer().start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                safe_value = _REDACTED if _is_sensitive_field(key) else value
                span.set_attribute(
                    key,
                    str(safe_value)
                    if not isinstance(safe_value, (str, bool, int, float))
                    else safe_value,
                )
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
