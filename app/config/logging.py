import logging
import logging.config
import structlog


def setup_logging(default_logger: str = "console", default_log_level: int = logging.INFO):
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
                    "handlers": [default_logger],
                    "level": default_log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [default_logger],
                    "level": default_log_level,
                    "propagate": False,
                },
                "django_structlog": {
                    "handlers": [default_logger],
                    "level": default_log_level,
                },
                "root": {
                    "handlers": [default_logger],
                    "level": default_log_level,
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
