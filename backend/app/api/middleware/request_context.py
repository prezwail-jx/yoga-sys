from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from opentelemetry.trace import Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.infra.observability import get_logger, get_tracer

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
        request.state.trace_id = trace_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        started = perf_counter()
        status_code = 500
        with get_tracer().start_as_current_span("http.request") as span:
            span_id = format(span.get_span_context().span_id, "016x")
            structlog.contextvars.bind_contextvars(span_id=span_id)
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("url.path", request.url.path)
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers["X-Trace-Id"] = trace_id
                span.set_status(Status(StatusCode.ERROR if status_code >= 500 else StatusCode.OK))
                return response
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            finally:
                duration_ms = round((perf_counter() - started) * 1000, 2)
                span.set_attribute("http.response.status_code", status_code)
                span.set_attribute("http.server.request.duration_ms", duration_ms)
                get_logger().info(
                    "http.request.complete", method=request.method, path=request.url.path,
                    status_code=status_code, duration_ms=duration_ms,
                )
                structlog.contextvars.clear_contextvars()
