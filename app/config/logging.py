"""
This module sets up logging configuration for the application using the standard logging library.
It defines multiple formatters and handlers to support different logging formats.

The `setup_logging` function will be called from various entry points (e.g., server, migrations) to initialize logging.
"""

import logging
import logging.config


def setup_logging(*handlers: str, log_level: str = "INFO"):
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "otel_formatter": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
            },
            "handlers": {
                "console": {
                    "class": "rich.logging.RichHandler",
                    "rich_tracebacks": True,
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
                    "level": logging.DEBUG,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "root": {
                    "handlers": handlers,
                    "level": log_level,
                },
            },
        }
    )
