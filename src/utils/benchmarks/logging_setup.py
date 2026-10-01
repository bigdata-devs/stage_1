"""Logging configuration for the benchmark entry points; importing a benchmark module never applies it."""

import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    """Prints INFO messages with timestamps; call it only from a ``__main__`` block."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
