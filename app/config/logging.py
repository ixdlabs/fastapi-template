"""
This module sets up logging configuration for the application using structlog and the standard logging library.
It defines multiple formatters and handlers to support different logging formats such as colored console output,
plain console output, and JSON format.

The `setup_logging` function will be called from various entry points (e.g., server, migrations) to initialize logging.

https://www.structlog.org/en/stable/console-output.html <br/>
https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging
"""

import logging
import logging.config
import structlog


def setup_logging(handler: str = "console", log_level: int = logging.INFO):
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
                "plain_console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.dev.ConsoleRenderer(colors=False),
                    ],
                },
                "json_formatter": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.add_log_level,
                        structlog.processors.TimeStamper(fmt="iso"),
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
                    "class": "logging.StreamHandler",
                    "formatter": "plain_console",
                },
                "json": {
                    "class": "logging.StreamHandler",
                    "formatter": "json_formatter",
                },
                "null": {
                    "class": "logging.NullHandler",
                },
            },
            "loggers": {
                "sqlalchemy.engine.Engine": {
                    "handlers": [handler],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [handler],
                    "level": log_level,
                    "propagate": False,
                },
                "django_structlog": {
                    "handlers": [handler],
                    "level": log_level,
                },
                "root": {
                    "handlers": [handler],
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
