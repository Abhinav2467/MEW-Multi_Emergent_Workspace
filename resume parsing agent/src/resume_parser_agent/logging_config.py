"""Logging setup for the application."""

import logging
import sys


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure process-wide structured-enough logging for local and Docker use."""

    logging.basicConfig(
        level=level.upper(),
        format=LOG_FORMAT,
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return an application logger."""

    return logging.getLogger(name)
