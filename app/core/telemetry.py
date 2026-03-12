import os
import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger.json import JsonFormatter


def setup_logging() -> None:
    """Configure root logger to emit structured JSON logs."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def setup_tracing(engine=None) -> None:
    """Initialize OTel tracer provider and instrument FastAPI + SQLAlchemy."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "todo-app")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def setup_telemetry(engine=None) -> None:
    """Bootstrap logging and distributed tracing for the application."""
    setup_logging()
    setup_tracing(engine)
