"""
Structured logging configuration using structlog.
Outputs JSON logs with automatic correlation ID binding.
"""

import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structlog for enterprise JSON logging.
    
    Pipeline:
      contextvars merge → add_log_level → timestamper → stack info
      → exc_info → JSON renderer
    """
    # Set stdlib logging level to match our setting
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level_upper, logging.INFO),
    )

    # Shared processors for both structlog and stdlib
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-readable for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.EventRenamer("message"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level_upper, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structlog logger instance for a module."""
    return structlog.get_logger(name)
