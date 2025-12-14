"""
This module sets up Open Telemetry instrumentation and exporters for the FastAPI application.
It configures tracing, metrics, and logging exporters based on the application settings.
Furthermore, this will reconfigure the logging to use the Open Telemetry log handler.

This should be called before the application starts handling requests.
Calling this from lifespan events is not recommended as the FastAPI instrumentation may not work correctly.

Open Telemetry Python Docs: https://opentelemetry-python-contrib.readthedocs.io
"""

from fastapi import FastAPI
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.instrumentation.threading import ThreadingInstrumentor
from opentelemetry.instrumentation.urllib import URLLibInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from app.config.database import create_db_engine_from_settings
from app.config.logging import setup_logging
from app.config.settings import Settings


def setup_open_telemetry(app: FastAPI, settings: Settings):
    if not settings.otel_enabled:
        return

    engine = create_db_engine_from_settings(settings)

    # Integrated Open Telemetry Python Libraries
    # https://opentelemetry-python-contrib.readthedocs.io
    AsyncioInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    SQLite3Instrumentor().instrument()
    ThreadingInstrumentor().instrument()
    URLLibInstrumentor().instrument()
    URLLib3Instrumentor().instrument()
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, enable_commenter=True)

    # Resource
    resource = Resource.create(
        attributes={
            "service.name": settings.otel_resource_service_name,
            "deployment.environment": settings.otel_resource_environment,
        }
    )

    # Set tracer provider
    span_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        headers=settings.otel_exporter_otlp_headers,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    span_processor = BatchSpanProcessor(span_exporter)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)
    set_tracer_provider(tracer_provider)

    # Set metric provider
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        headers=settings.otel_exporter_otlp_headers,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    set_meter_provider(meter_provider)

    # Set logger provider
    log_exporter = OTLPLogExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        headers=settings.otel_exporter_otlp_headers,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(log_processor)
    set_logger_provider(logger_provider)

    # Reconfigure logging to use Open Telemetry handler
    setup_logging(settings.logger_name, "otel")
