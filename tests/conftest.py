"""Shared pytest configuration for the Stage 1 test suite."""

import logging

SOURCE_LOGGER_NAME = "src"


def pytest_configure() -> None:
    """Keeps application logs out of the test output while assertLogs can still capture them."""
    source_logger = logging.getLogger(SOURCE_LOGGER_NAME)
    source_logger.addHandler(logging.NullHandler())
    source_logger.propagate = False
