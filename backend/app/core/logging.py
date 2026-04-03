"""Shared logging configuration."""

import logging


def configure_logging() -> None:
    """Configure root logger with a standard format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
