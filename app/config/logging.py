"""
This module sets up logging configuration for the application using structlog and the standard logging library.
It defines multiple formatters and handlers to support different logging formats.

The `setup_logging` function will be called from various entry points (e.g., server, migrations) to initialize logging.

https://www.structlog.org/en/stable/console-output.html <br/>
https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging
"""

import logging
import logging.config
import structlog


def setup_logging(*handlers: str, log_level: str = "INFO"):
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "colored_console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.dev.ConsoleRenderer(colors=True),
                    ],
                },
                "otel_formatter": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.stdlib.add_logger_name,
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),
                    ],
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "colored_console",
                },
                "otel": {
                    "class": "opentelemetry.sdk._logs.LoggingHandler",
                    "formatter": "otel_formatter",
                },
                "null": {
                    "class": "logging.NullHandler",
                },
            },
            "loggers": {
                "sqlalchemy.engine.Engine": {
                    "handlers": handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "django_structlog": {
                    "handlers": handlers,
                    "level": log_level,
                },
                "root": {
                    "handlers": handlers,
                    "level": log_level,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
