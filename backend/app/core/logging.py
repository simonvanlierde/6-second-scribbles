"""Shared logging configuration using structlog.

Wraps stdlib logging so existing ``logging.getLogger(__name__)`` calls
automatically benefit from structured processing. Dev gets coloured
console output; prod gets JSON lines.
"""

import logging
import sys

import structlog

from app.core.config import CURRENT_ENV, ENV


def configure_logging() -> None:
    """Configure structlog + stdlib logging for the current environment."""
    is_prod = CURRENT_ENV == ENV.PROD

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_prod:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Ensure stdlib loggers propagate to root so pytest's caplog fixture
    # continues to capture log output during tests.
    for name in logging.Logger.manager.loggerDict:
        logging.getLogger(name).propagate = True
