from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.infra.observability import business_span, configure_observability

def test_business_span_exports_safe_business_attributes():
    configure_observability()
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with business_span("transaction.apply", **{"business.action": "purchase", "actor.role": "admin"}):
        pass
    span = exporter.get_finished_spans()[-1]
    assert span.name == "transaction.apply"
    assert span.attributes["business.action"] == "purchase"
    assert span.attributes["actor.role"] == "admin"
    assert span.status.status_code.name == "OK"
