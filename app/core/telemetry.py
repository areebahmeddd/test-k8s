import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger.json import JsonFormatter
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings


def setup_logging() -> None:
    """Emit JSON logs on the root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "otelTraceID": "trace_id",
                "otelSpanID": "span_id",
                "otelTraceSampled": "trace_sampled",
                "otelServiceName": "service_name",
            },
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)


def setup_tracing(app: FastAPI, engine: AsyncEngine) -> None:
    """Export spans over OTLP, instrument FastAPI and SQLAlchemy, and add trace ids to logs.

    The exporter and resource read the standard OTEL_* environment variables
    (OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME).
    """
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    LoggingInstrumentor().instrument(inject_trace_context=True)


def setup_telemetry(app: FastAPI, engine: AsyncEngine) -> None:
    """Configure structured logging, and tracing when an OTLP endpoint is set."""
    setup_logging()
    if settings.otel_exporter_otlp_endpoint:
        setup_tracing(app, engine)
