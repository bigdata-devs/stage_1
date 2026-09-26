"""Test suite for the Stage 1 search engine. Run with: python -m unittest discover -s tests -t ."""

import logging

# Keep test output clean without disabling logging, so assertLogs still works.
logging.getLogger("src").addHandler(logging.NullHandler())
logging.getLogger("src").propagate = False
